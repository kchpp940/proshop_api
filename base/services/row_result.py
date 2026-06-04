from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RowResult:
    row_number: int
    status: str
    product_id: Optional[int] = None
    product_name: str = ''
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self):
        return {
            'row_number': self.row_number,
            'status': self.status,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'errors': self.errors,
            'warnings': self.warnings,
        }
