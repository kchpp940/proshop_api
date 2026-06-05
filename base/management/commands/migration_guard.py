import os
import re
import sys
import ast
from collections import defaultdict
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import connections
from django.apps import apps
from django.db.migrations.loader import MigrationLoader


class MigrationGuard:
    def __init__(self, options=None):
        self.options = options or {}
        self.errors = []
        self.warnings = []
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.migration_pattern = re.compile(r'^(\d{4})_.*\.py$')

    def log_error(self, message, file_path=None, fix_suggestion=None):
        error = {'message': message, 'file': file_path, 'fix': fix_suggestion}
        self.errors.append(error)

    def log_warning(self, message, file_path=None, fix_suggestion=None):
        warning = {'message': message, 'file': file_path, 'fix': fix_suggestion}
        self.warnings.append(warning)

    def get_all_migration_dirs(self):
        migration_dirs = []
        project_root = self.base_dir
        for app_config in apps.get_app_configs():
            migrations_dir = Path(app_config.path) / 'migrations'
            if migrations_dir.exists():
                try:
                    app_path = Path(app_config.path).resolve()
                    if project_root in app_path.parents or app_path == project_root:
                        migration_dirs.append((app_config.label, migrations_dir))
                except Exception:
                    pass
        return migration_dirs

    def check_duplicate_numbers(self):
        self.print_header('Checking for duplicate migration numbers (same-app unmerged branches)')
        try:
            loader = MigrationLoader(connections['default'])
            graph = loader.graph
        except Exception:
            graph = None

        for app_label, migrations_dir in self.get_all_migration_dirs():
            numbers = defaultdict(list)
            for f in migrations_dir.iterdir():
                if f.is_file() and f.name != '__init__.py' and f.suffix == '.py':
                    match = self.migration_pattern.match(f.name)
                    if match:
                        num = match.group(1)
                        numbers[num].append(f.name)

            for num, files in numbers.items():
                if len(files) <= 1:
                    continue

                if graph is not None:
                    same_num_leaves = []
                    for fname in files:
                        key = (app_label, Path(fname).stem)
                        if key in graph.node_map:
                            descendants = graph.forwards_plan(key)
                            has_downstream = any(
                                desc[0] == app_label and desc != key
                                for desc in descendants
                            )
                            if not has_downstream:
                                same_num_leaves.append(fname)
                    if len(same_num_leaves) >= 2:
                        self.log_error(
                            f"App '{app_label}' has unmerged branch at number {num}: {', '.join(same_num_leaves)}",
                            file_path=str(migrations_dir),
                            fix_suggestion=f"Run 'python manage.py makemigrations --merge {app_label}' to create a merge migration."
                        )
                    elif same_num_leaves:
                        self.log_warning(
                            f"App '{app_label}' has same-number migrations at {num}: {', '.join(files)} (already merged downstream)",
                            file_path=str(migrations_dir),
                            fix_suggestion="No action needed — the branches are merged. "
                                           "Consider squashing migrations if the history is overly complex."
                        )
                    else:
                        self.log_warning(
                            f"App '{app_label}' has same-number migrations at {num}: {', '.join(files)} (all merged downstream)",
                            file_path=str(migrations_dir),
                            fix_suggestion="No action needed — the branches are merged. "
                                           "Consider squashing migrations if the history is overly complex."
                        )
                else:
                    self.log_warning(
                        f"App '{app_label}' has same-number migrations at {num}: {', '.join(files)} (graph unavailable, cannot determine merge status)",
                        file_path=str(migrations_dir),
                        fix_suggestion="Run 'python manage.py makemigrations --merge' if these represent unmerged branches."
                    )

    def check_missing_dependencies(self):
        self.print_header('Checking for missing migration dependencies')
        try:
            loader = MigrationLoader(connections['default'])
        except Exception as e:
            self.log_error(
                f"Failed to load migrations: {e}",
                fix_suggestion="Check for missing or corrupted migration files. Ensure all dependencies exist."
            )
            return

        for app_label, migrations_dir in self.get_all_migration_dirs():
            for f in migrations_dir.iterdir():
                if not f.is_file() or f.name == '__init__.py' or f.suffix != '.py':
                    continue

                match = self.migration_pattern.match(f.name)
                if not match:
                    if f.name != 'update_image_urls.py':
                        self.log_warning(
                            f"Non-standard migration filename: {f.name}",
                            file_path=str(f),
                            fix_suggestion="Rename to follow the pattern NNNN_description.py"
                        )
                    continue

                migration_name = f.stem
                try:
                    with open(f, 'r') as fp:
                        tree = ast.parse(fp.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name) and target.id == 'dependencies':
                                            if isinstance(item.value, ast.List):
                                                for dep in item.value.elts:
                                                    if isinstance(dep, ast.Tuple) and len(dep.elts) == 2:
                                                        dep_app = dep.elts[0].s if isinstance(dep.elts[0], ast.Constant) else None
                                                        dep_name = dep.elts[1].s if isinstance(dep.elts[1], ast.Constant) else None

                                                        if dep_app and dep_name:
                                                            dep_key = (dep_app, dep_name)
                                                            if dep_app != '__setting__' and dep_key not in loader.disk_migrations:
                                                                dep_file = migrations_dir / f"{dep_name}.py"
                                                                if not dep_file.exists():
                                                                    self.log_error(
                                                                        f"Migration {app_label}/{migration_name} depends on non-existent migration: {dep_app}.{dep_name}",
                                                                        file_path=str(f),
                                                                        fix_suggestion=f"Create the missing migration {dep_name}.py in {dep_app}/migrations/, "
                                                                                       f"or update the dependency to point to an existing migration."
                                                                    )
                except SyntaxError as e:
                    self.log_error(
                        f"Syntax error in migration file {f.name}: {e}",
                        file_path=str(f),
                        fix_suggestion="Fix the Python syntax error in the migration file."
                    )

    def check_migration_graph(self):
        self.print_header('Checking migration graph integrity')
        try:
            loader = MigrationLoader(connections['default'])
            graph = loader.graph
        except Exception as e:
            self.log_error(
                f"Failed to load migration graph: {e}",
                fix_suggestion="Check for missing or corrupted migration files. Ensure all dependencies exist."
            )
            return

        try:
            leaf_nodes = graph.leaf_nodes()
            leaf_by_app = defaultdict(list)
            for app, name in leaf_nodes:
                leaf_by_app[app].append(name)

            for app, leaves in leaf_by_app.items():
                if len(leaves) > 1:
                    self.log_error(
                        f"App '{app}' has {len(leaves)} leaf migrations: {', '.join(leaves)}",
                        fix_suggestion=f"Run 'python manage.py makemigrations --merge {app}' to merge the leaf migrations "
                                       f"into a single migration that depends on all of them."
                    )

            try:
                graph.ensure_not_cyclic()
            except Exception as e:
                self.log_error(
                    f"Cyclic dependency detected in migration graph: {e}",
                    fix_suggestion="Review migration dependencies and remove the cycle by adjusting the dependency chain."
                )

        except Exception as e:
            self.log_error(
                f"Failed to build migration graph: {e}",
                fix_suggestion="Check for corrupted migration files or missing dependencies."
            )

    def check_ungenerated_migrations(self):
        self.print_header('Checking for ungenerated migrations (model changes not in migrations)')
        try:
            loader = MigrationLoader(connections['default'])
        except Exception as e:
            self.log_warning(
                f"Could not check for ungenerated migrations: {e}",
                fix_suggestion="Manually run 'python manage.py makemigrations --check --dry-run' to verify."
            )
            return

        try:
            from django.db.migrations.autodetector import MigrationAutodetector
            from django.db.migrations.state import ProjectState

            project_state = loader.project_state(None)
            autodetector = MigrationAutodetector(
                project_state,
                ProjectState.from_apps(apps),
                True,
            )
            changes = autodetector.changes(graph=loader.graph)

            if changes:
                for app, migrations in changes.items():
                    for migration in migrations:
                        ops_descriptions = [str(op) for op in migration.ops]
                        self.log_error(
                            f"App '{app}' has ungenerated migration: {migration.name}\n"
                            f"  Operations: {'; '.join(ops_descriptions)}",
                            fix_suggestion=f"Run 'python manage.py makemigrations {app}' to generate the migration file "
                                           f"for the model changes."
                        )
        except Exception as e:
            self.log_warning(
                f"Could not check for ungenerated migrations: {e}",
                fix_suggestion="Manually run 'python manage.py makemigrations --check --dry-run' to verify."
            )

    def check_dangerous_operations(self):
        self.print_header('Checking for dangerous operations (DeleteModel, RemoveField, etc.)')
        dangerous_ops = {
            'DeleteModel': 'WARNING: Deletes an entire model and its table',
            'RemoveField': 'WARNING: Removes a field and its column',
            'AlterUniqueTogether': 'May cause index rebuilds on large tables',
            'AddField': 'May require default values for existing rows',
        }

        for app_label, migrations_dir in self.get_all_migration_dirs():
            for f in migrations_dir.iterdir():
                if not f.is_file() or f.name == '__init__.py' or f.suffix != '.py':
                    continue
                if not self.migration_pattern.match(f.name):
                    continue

                try:
                    with open(f, 'r') as fp:
                        content = fp.read()
                        tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Attribute):
                                op_name = node.func.attr
                                if op_name in dangerous_ops:
                                    level = 'error' if op_name in ['DeleteModel', 'RemoveField'] else 'warning'
                                    msg = f"Migration {app_label}/{f.stem} contains dangerous operation: {op_name}"
                                    fix = f"Review the {op_name} operation carefully. "

                                    if op_name == 'DeleteModel':
                                        fix += "Ensure there is a data migration to backup data first. " \
                                               "Consider using --fake if the table was already removed manually."
                                    elif op_name == 'RemoveField':
                                        fix += "Ensure there is a data migration to backup data first. " \
                                               "Make sure the field is not used anywhere in the codebase."
                                    elif op_name == 'AddField':
                                        fix += "Ensure the field has a proper default value for existing rows, " \
                                               "or make it nullable."

                                    if level == 'error':
                                        self.log_error(msg, file_path=str(f), fix_suggestion=fix)
                                    else:
                                        self.log_warning(msg, file_path=str(f), fix_suggestion=fix)

                except SyntaxError:
                    pass

    def check_migration_model_consistency(self):
        self.print_header('Checking migration and model consistency')
        try:
            loader = MigrationLoader(connections['default'])
        except Exception as e:
            self.log_error(
                f"Failed to load migrations for consistency check: {e}",
                fix_suggestion="Check for missing or corrupted migration files. Ensure all dependencies exist."
            )
            return

        try:
            applied = set(loader.applied_migrations)
            disk = set(loader.disk_migrations.keys())

            unapplied = disk - applied
            missing = applied - disk

            if unapplied:
                unapplied_list = [f"{app}.{name}" for app, name in sorted(unapplied)]
                self.log_warning(
                    f"Unapplied migrations found: {', '.join(unapplied_list)}",
                    fix_suggestion="Run 'python manage.py migrate' to apply pending migrations."
                )

            if missing:
                missing_list = [f"{app}.{name}" for app, name in sorted(missing)]
                self.log_error(
                    f"Migrations applied to database but missing from disk: {', '.join(missing_list)}",
                    fix_suggestion="Restore the missing migration files from version control, "
                                   "or use 'python manage.py migrate --fake {app} {migration}' to skip them."
                )

        except Exception as e:
            self.log_warning(
                f"Could not check migration consistency: {e}",
                fix_suggestion="Ensure database is accessible and settings are correctly configured."
            )

    def print_header(self, title):
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")

    def print_results(self):
        print(f"\n{'=' * 60}")
        print(f"  MIGRATION GUARD SUMMARY")
        print(f"{'=' * 60}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"\n  {i}. {error['message']}")
                if error['file']:
                    print(f"     File: {error['file']}")
                if error['fix']:
                    print(f"     Fix:  {error['fix']}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"\n  {i}. {warning['message']}")
                if warning['file']:
                    print(f"     File: {warning['file']}")
                if warning['fix']:
                    print(f"     Fix:  {warning['fix']}")

        if not self.errors and not self.warnings:
            print("\n✅ All checks passed! No issues found.")
        elif self.errors:
            print(f"\n❌ FAILED with {len(self.errors)} error(s) and {len(self.warnings)} warning(s).")
        else:
            print(f"\n⚠️  PASSED with {len(self.warnings)} warning(s).")

        print(f"\n{'=' * 60}\n")

    def run_all_checks(self):
        print("\n🔍 Running Migration Guard - Database Migration Pre-Deployment Check")
        print("=" * 60)

        self.check_duplicate_numbers()
        self.check_dangerous_operations()
        self.check_missing_dependencies()
        self.check_migration_graph()
        self.check_migration_model_consistency()
        self.check_ungenerated_migrations()

        self.print_results()

        return len(self.errors) == 0


class Command(BaseCommand):
    help = 'Run migration guard checks before deployment to ensure migration integrity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only run checks, do not fail even if errors are found',
        )
        parser.add_argument(
            '--warn-only',
            action='store_true',
            help='Treat errors as warnings, do not fail',
        )

    def handle(self, *args, **options):
        import django
        django.setup()

        guard = MigrationGuard(options)
        success = guard.run_all_checks()

        if not success and not options.get('check_only') and not options.get('warn_only'):
            sys.exit(1)

        if guard.errors and options.get('warn_only'):
            self.stdout.write(self.style.WARNING("Errors found but --warn-only specified, not failing."))
