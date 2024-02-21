from django.contrib import admin

from .models import AuctionListing, Comment, Bid, Watchlist


# Register your models here.
admin.site.register(AuctionListing)
admin.site.register(Comment)
admin.site.register(Bid)
admin.site.register(Watchlist)
