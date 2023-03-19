from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from .models import Customer
import razorpay
from project1.settings import RAZORPAY_API_KEY, RAZORPAY_API_SECRET_KEY
from django.views import View
from .models import Products
from .models import Order
from .models import Category
from .auth import  auth_middleware
from project1.settings import BASE_DIR
from django.contrib import messages

def about_us(request):
    return render(request, 'about_us.html')

class Login(View):
    return_url = None
    def get(self, request):
        Login.return_url = request.GET.get ('return_url')
        return render (request, 'login.html')

    def post(self, request):
        email = request.POST.get ('email')
        password = request.POST.get ('password')
        customer = Customer.get_customer_by_email(email)
        error_message = None
        if customer:
            flag = check_password (password, customer.password)
            if flag:
                request.session['customer'] = customer.id
                if Login.return_url:
                    return HttpResponseRedirect (Login.return_url)
                else:
                    Login.return_url = None
                    messages.success(request, 'Logged In Successfully')
                    return redirect ('homepage')
            else:
                error_message = 'Invalid Credentials.!'
        else:
            error_message = 'Invalid Credentials.!'
        return render (request, 'login.html', {'error': error_message})

def logout(request):
    request.session.clear()
    return redirect('homepage')

class Signup (View):
    def get(self, request):
        return render (request, 'signup.html')
    def post(self, request):
        error_message = None
        postData = request.POST
        first_name = postData.get ('firstname')
        last_name = postData.get ('lastname')
        phone = postData.get ('phone')
        email = postData.get ('email')
        password = postData.get ('password')
        value = {'first_name': first_name, 'last_name': last_name, 'phone': phone, 'email': email}
        customer = Customer (first_name=first_name, last_name=last_name, phone=phone, email=email, password=password)
        error_message = self.validateCustomer (customer)
        if not error_message:
            customer.password = make_password (customer.password)
            customer.register ()
            messages.success(request, 'Account Created Successfully')
            return redirect ('login')
        else:
            data = {'error': error_message, 'values': value}
            messages.warning(request, 'Error creating Account')
            return render (request, 'signup.html', data)

    def validateCustomer(self, customer):
        error_message = None
        if customer.isExists ():
            error_message = 'Email is alrealdy registered, please try different one.!'
        return error_message


class Cart(View):
    def get(self , request):
        ids = list(request.session.get('cart').keys())
        products = Products.get_products_by_id(ids)
        return render(request , 'cart.html' , {'products' : products} )


class CheckOut(View):
    def post(self, request):
        client = razorpay.Client(auth=(RAZORPAY_API_KEY, RAZORPAY_API_SECRET_KEY))
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        customer = request.session.get('customer')
        cart = request.session.get('cart')
        products = Products.get_products_by_id(list(cart.keys()))
        total_price = 0
        if products:
            for product in products:
                total_price += (product.price * cart.get(str(product.id)))
                order = Order(customer=Customer(id=customer), product=product, price=product.price, address=address, phone=phone, quantity=cart.get(str(product.id)))
                order.save()
            display_amount = total_price
            total_price *= 100
            payment_order=client.order.create(dict(amount=total_price,currency='INR', payment_capture=1))
            payment_order_id=payment_order['id']
            request.session['cart'] = {}
            return render(request,'pay.html',{"api_key":RAZORPAY_API_KEY,"amount":total_price,"order_id":payment_order_id,"display_amount":display_amount})
        else:
            messages.warning(request, 'No Items in the cart. Please add some.!!')
            return redirect("store")


class Index(View):
    def post(self , request):
        product = request.POST.get('product')
        remove = request.POST.get('remove')
        cart = request.session.get('cart')
        if cart:
            quantity = cart.get(product)
            if quantity:
                if remove:
                    if quantity<=1:
                        cart.pop(product)
                    else:
                        cart[product]  = quantity-1
                else:
                    cart[product]  = quantity+1

            else:
                cart[product] = 1
        else:
            cart = {}
            cart[product] = 1
        request.session['cart'] = cart
        return redirect('homepage')

    def get(self , request):
        return HttpResponseRedirect(f'/store{request.get_full_path()[1:]}')

def store(request):
    cart = request.session.get('cart')
    if not cart:
        request.session['cart'] = {}
    products = None
    categories = Category.get_all_categories()
    categoryID = request.GET.get('category')
    if categoryID:
        products = Products.get_all_products_by_categoryid(categoryID)
    else:
        products = Products.get_all_products()
    data = {}
    data['products'] = products
    data['categories'] = categories
    return render(request, 'index.html', data)


class OrderView(View):
    def get(self , request ):
        customer = request.session.get('customer')
        orders = Order.get_orders_by_customer(customer)
        return render(request , 'orders.html'  , {'orders' : orders})


client = razorpay.Client(auth=(RAZORPAY_API_KEY, RAZORPAY_API_SECRET_KEY))
def pay(request):
    order_amount=40000
    order_currency='IN'
    payment_order=client.order.create(dict(amount=order_amount,currency=order_currency, payment_capture=1))
    payment_order_id=payment_order['id']
    context ={'amount':order_amount,'api_key':RAZORPAY_API_KEY,'order_id':payment_order_id}
    return render(request,'pay.html', context)