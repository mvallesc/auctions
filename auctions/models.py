from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class AuctionListing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    starting_bid = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seller = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="auctions")
    winner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="won_auctions")


    def save(self, *args, **kwargs):
        # Si no hay un precio actual, establecerlo como la oferta inicial al guardar
        if not self.current_price:
            self.current_price = self.starting_bid
        super().save(*args, **kwargs)

    def update_current_price(self, new_bid_amount):
        # Actualizar el precio actual al recibir una nueva oferta
        if new_bid_amount > self.current_price:
            self.current_price = new_bid_amount
            self.save()

    def close_auction(self):
        bids = Bid.objects.filter(listing=self)
        if bids.exists():
            winning_bid = bids.order_by('-amount').first()
            self.winner = winning_bid.user
            self.is_active = False
            self.update_current_price(winning_bid.amount)
            self.save()


class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)


class Bid(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listing = models.ForeignKey(AuctionListing, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)


class Comment(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comments")
    auction = models.ForeignKey(
        AuctionListing, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
