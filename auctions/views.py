from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required



from .models import User, AuctionListing, Watchlist, Bid, Comment
from .forms import CreateListingForm


def index(request):
    active_listings = AuctionListing.objects.filter(
        is_active=True).order_by('-created_at')
    return render(request, 'auctions/index.html', {'active_listings': active_listings})


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


@login_required(login_url='login')
def create_listing(request):
    if request.method == 'POST':
        form = CreateListingForm(request.POST)
        if form.is_valid():
            # Crea una nueva instancia de AuctionListing con los datos del formulario pero no lo guarda en la base de datos
            new_listing = form.save(commit=False)
            new_listing.seller = request.user
            # Establecer el precio actual como la oferta inicial
            new_listing.current_price = new_listing.starting_bid
            new_listing.save()
            messages.success(request, 'Listing created successfully!')
            return redirect('index')
        else:
            messages.error(
                request, 'Error in the form submission. Please check the details.')
    else:
        form = CreateListingForm()

    return render(request, 'auctions/create_listing.html', {'form': form})



def listing_page(request, listing_id):
    listing = get_object_or_404(AuctionListing, pk=listing_id)

    # Verifica si el usuario actual tiene este listado en su Watchlist
    in_watchlist = False
    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(
            user=request.user, listing=listing).exists()

    # Obtén todas las ofertas para esta subasta
    bids = Bid.objects.filter(listing=listing).order_by('-amount')

    # Verifica si el usuario ganó la subasta
    user_won = False
    if request.user.is_authenticated and listing.is_active == False and listing.winner == request.user:
        user_won = True

    if request.method == 'POST' and 'bid_amount' in request.POST:
        bid_amount = float(request.POST['bid_amount'])

        # Verifica que la oferta sea válida
        if listing.is_active and bid_amount > listing.starting_bid and (not bids or bid_amount > bids[0].amount) and request.user != listing.seller:
            # Crea una nueva oferta
            Bid.objects.create(user=request.user,
                               listing=listing, amount=bid_amount)
            # Actualiza el precio actual de la subasta
            listing.update_current_price(bid_amount)
            messages.success(request, 'Bid placed successfully!')
            return redirect('listing_page', listing_id=listing.id)
        elif request.user == listing.seller:
             messages.error(
                request, "You can't bid on your own listing.")
        elif not listing.is_active:
            messages.error(
                request, 'This auction is closed. No more bids are allowed.')
        else:
            messages.error(
                request, 'Invalid bid amount. Please check the details.')

    # Verifica si el usuario actual es el creador del listado y si la subasta está activa
    can_close_auction = request.user == listing.seller and listing.is_active

    if request.method == 'POST' and 'close_auction' in request.POST and can_close_auction:
        # Cierra la subasta si el usuario actual es el creador y la subasta está activa
        listing.close_auction()
        messages.success(request, 'Auction closed successfully!')
        return redirect('listing_page', listing_id=listing.id)

    # Maneja la creación de comentarios
    if request.method == 'POST' and 'comment_content' in request.POST:
        comment_content = request.POST['comment_content']
        Comment.objects.create(
            user=request.user, auction=listing, content=comment_content)

    # Obtiene todos los comentarios asociados a esta subasta
    comments = Comment.objects.filter(auction=listing).order_by('created_at')

    return render(request, 'auctions/listing_page.html', {'listing': listing, 'in_watchlist': in_watchlist, 'bids': bids, 'can_close_auction': can_close_auction, 'user_won': user_won, 'comments': comments})



@login_required
def add_to_watchlist(request, listing_id):
    listing = get_object_or_404(AuctionListing, pk=listing_id)
    Watchlist.objects.create(user=request.user, listing=listing)
    # Redirige al usuario de vuelta a la pagina desde la cual provino, o a la pagina de inicio ('/') si no hay informacion de referencia disponible en la solicitud HTTP
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def remove_from_watchlist(request, listing_id):
    listing = get_object_or_404(AuctionListing, pk=listing_id)
    Watchlist.objects.filter(user=request.user, listing=listing).delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='login')
def watchlist(request):
    watchlist_items = Watchlist.objects.filter(user=request.user)
    return render(request, 'auctions/watchlist.html', {'watchlist_items': watchlist_items})


def categories(request):
    all_categories = AuctionListing.objects.values_list(
        'category', flat=True).distinct()
    return render(request, 'auctions/categories.html', {'all_categories': all_categories})


def category_listings(request, category):
    if category == 'None':
        # Filtrar listings sin categoría
        listings = AuctionListing.objects.filter(
            category__isnull=True, is_active=True)
    else:
        # Filtrar listings por categoría
        listings = AuctionListing.objects.filter(
            category=category, is_active=True)

    return render(request, 'auctions/index.html', {'category': category, 'active_listings': listings})
