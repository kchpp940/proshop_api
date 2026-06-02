from django.db import transaction
from django.db.models import Avg, Count

from base.models import Product, Review


class ProductNotFound(ValueError):
    pass


class ReviewNotFound(ValueError):
    pass


class ReviewValidationError(ValueError):
    pass


class ReviewPermissionDenied(PermissionError):
    pass


class ProductReviewService:
    @staticmethod
    def recalculate_product_rating(product):
        if product is None:
            return
        agg = product.review_set.filter(
            rating__isnull=False
        ).aggregate(
            avg_rating=Avg('rating'),
            total=Count('_id')
        )
        product.numReviews = agg['total'] or 0
        product.rating = round(agg['avg_rating'], 2) if agg['avg_rating'] is not None else 0
        product.save()

    @staticmethod
    @transaction.atomic
    def create_review(user, product_id, rating, comment):
        try:
            product = Product.objects.select_for_update().get(_id=product_id)
        except Product.DoesNotExist:
            raise ProductNotFound('Product not found')

        existing_reviews = product.review_set.select_for_update().filter(user=user)
        if existing_reviews.exists():
            raise ReviewValidationError('Product already reviewed')

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise ReviewValidationError('Rating must be a number between 1 and 5')

        if not (1 <= rating <= 5):
            raise ReviewValidationError('Rating must be between 1 and 5')

        if comment is None or str(comment).strip() == '':
            raise ReviewValidationError('Comment cannot be empty')

        review_name = f'{user.first_name} {user.last_name}'.strip() or user.email

        Review.objects.create(
            user=user,
            product=product,
            name=review_name,
            rating=rating,
            comment=str(comment).strip(),
        )

        return product

    @staticmethod
    @transaction.atomic
    def delete_review(review_id, user):
        try:
            review = Review.objects.select_related('product').get(_id=review_id)
        except Review.DoesNotExist:
            raise ReviewNotFound('Review not found')

        if review.user != user and not user.is_staff:
            raise ReviewPermissionDenied('You are not authorized to delete this review')

        review.delete()
