from django.shortcuts import render_to_response, redirect
from lostpet_auth.models import *
from django.template import RequestContext
from django.contrib.auth.models import *

from functools import wraps

import datetime
from django.http import HttpResponse
from lostpet import settings

import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q

from allauth.socialaccount.models import SocialAccount
import os
import stripe
import mailchimp

# Login Required decorator
def login_required():
    def login_decorator(function):
        @wraps(function)
        def wrapped_function(request):

            # if a user is not authorized, redirect to login page
            if 'user' not in request.session or request.session['user'] is None:
                return redirect("/")
            # otherwise, go on the request
            else:
                return function(request)

        return wrapped_function

    return login_decorator


# login view
def login(request):
    error = 'none'
    request.session['user'] = None

    if 'username' in request.POST:

        # get username and password from request.
        username = request.POST['username']
        password = request.POST['password']

        # check whether the user is in database or not
        if username == settings.ADMIN_NAME and password == settings.ADMIN_PASSWORD:
            request.session['user'] = {
                # "id": user[0].id,
                "username": settings.ADMIN_NAME, #user[0].email,
                "password": settings.ADMIN_PASSWORD, #user[0].name.split(" ")[0],
                "role": "admin"
            }

            return redirect("/admin_main")

        user = Client.objects.filter(email=username, password=password)

        if len(user) > 0:
            request.session['user'] = {
                # "id": user[0].id,
                "username": user[0].name.split(" ")[0],
                "email": user[0].email,
                "password": user[0].password,
                "role": "client"
            }

            return redirect("/pricing")
        else:
            error = 'block'

    return render_to_response('login.html', {'error':error}, context_instance=RequestContext(request))


# logout view
#   initialize session variable
def logout(request):
    request.session['user'] = None
    return redirect("/")

@login_required()
def main(request):
    clients = Client.objects.all().order_by("-created_on")
    return render_to_response('blank.html', locals(), context_instance=RequestContext(request))

@login_required()
def admin_main(request):
    if request.session["user"]["role"] != "admin":
        return redirect("/")

    clients = Client.objects.all().order_by("-created_on")
    return render_to_response('main.html', locals(), context_instance=RequestContext(request))

@login_required()
def create(request):
    breeds = settings.BREED

    if request.POST:
        client = Client()
        client.name = request.POST["client_name"]
        client.email = request.POST["email"]
        client.password = request.POST["password"]
        client.pet_name = request.POST["pet_name"]
        client.type = request.POST["type"]
        client.size = request.POST["size"]
        client.breed = request.POST["breed"]
        client.color = request.POST["color"]
        client.sex = request.POST["sex"]
        client.state = request.POST["state"]
        client.zip_code = request.POST["zip_code"]
        client.date = "%s 00:00" % request.POST["date"]

        client.save()

        # subscribe in mailchimp
        merge_vars = {
              "FNAME": client.name,
              "PNAME": client.pet_name,
              "PTYPE": client.type,
              "GROUPINGS": [
                    {
                        "name": "Leads",
                        "groups":["Website Lead"]
                    }
                ]
        }
        api = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
        api.lists.subscribe(settings.MAILCHIMP_LIST_ID, {"email": client.email}, merge_vars)

        return redirect("/admin_main")

    return render_to_response('create.html', locals(), context_instance=RequestContext(request))

@login_required()
def remove(request):
    id = request.GET["id"]
    client = Client.objects.get(pk=id)

    #api = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
    #api.lists.unsubscribe(settings.MAILCHIMP_LIST_ID, {"email": client.email})

    client.delete()

    return redirect("/admin_main")

@login_required()
def remove_history(request):
    Pet.objects.all().delete()

    return redirect("/admin_main")

def signup(request):
    breeds = settings.BREED
    
    if request.POST:
        client = Client()
        client.name = "%s %s" % (request.POST["firstname"], request.POST["lastname"])
        client.email = request.POST["email"]
        client.password = request.POST["password"]
        client.pet_name = request.POST["petname"]
        client.type = request.POST["type"]
        client.size = request.POST["size"]
        client.breed = request.POST["breed"]
        client.mixed = request.POST["mixed"]
        client.color = request.POST["color"]
        client.sex = request.POST["sex"]

        date = request.POST["date"].split("/")
        date = "%s-%s-%s 00:01" % (date[2], date[0], date[1])
        client.date = datetime.datetime.strptime(date,"%Y-%m-%d %H:%M")

        client.state = request.POST["state"]
        client.zip_code = request.POST["zipcode"]
        client.microchip = int(request.POST["microchip"])
        client.collar = int(request.POST["collar"])
        client.description = request.POST["description"]   

        if "pet_image" in request.FILES:
            client.pet_image = save_file(request.FILES["pet_image"])

        client.save()

        # subscribe in mailchimp
        merge_vars = {
              "FNAME": request.POST["firstname"],
              "LNAME": request.POST["lastname"],
              "PNAME": client.pet_name,
              "PTYPE": client.type,
              "PIMAGE": client.pet_image,
              "CITY": client.state,
              "GROUPINGS": [
                    {
                        "name": "Leads",
                        "groups":["Website Lead"]
                    }
                ]
        }
        api = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
        print api.lists.subscribe(settings.MAILCHIMP_LIST_ID, {"email": client.email}, merge_vars)

        return redirect("/pricing")

    return render_to_response('signup.html', locals(), context_instance=RequestContext(request))

def save_file(file, path='images', filename=""):
    temp = settings.BASE_DIR + settings.STATIC_URL + str(path)

    if not os.path.exists(temp):
        os.makedirs(temp)

    if filename == "":
        filename = file._get_name()
    
    fd = open('%s/%s' % (temp, str(filename)), 'wb')
    for chunk in file.chunks():
        fd.write(chunk)
    fd.close()

    return filename

# check email duplication
@csrf_exempt
def check_duplication(request):
    res = {"result": "false"}

    email = request.POST["email"]
    if len(Client.objects.filter(email=email)) > 0:
        res["result"] = "true"

    return HttpResponse(json.dumps(res)) 

@login_required()
def pricing(request):
    stripe_pk = settings.STRIPE_PUBLIC_KEY

    if "email" not in request.session['user']:
        return redirect("/main")

    client = Client.objects.filter(email=request.session['user']["email"])[0]
    price = Client.objects.filter(email=request.session['user']["email"])[0].pricing

    return render_to_response('pricing.html', locals(), context_instance=RequestContext(request))

def setup_pricing(request):
    return redirect("/accounts/stripe/login/?process=login&next=/setup_info?price=" + request.GET["price"])

def setup_info(request):
    '''tp_user = User.objects.filter(username=request.user)
    stripe_uid = SocialAccount.objects.filter(user=tp_user[0], provider="stripe")[0]	
    data = stripe_uid.extra_data
    
    client = Client.objects.filter(email=data['email'])

    if len(client) == 0:
        return redirect("/pricing")

    client = client[0]
    client.pricing = request.GET["price"]
    client.save()'''

    # subscribe a price in stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    charge = stripe.Charge.create(
        amount= int(request.GET["price"]) * 100,
        currency="usd",
        source=request.GET['token'],
        description='Sent the money!'
    )

    client = Client.objects.filter(email=request.session['user']["email"])[0]
    client.pricing = int(request.GET["price"])
    client.save()

    # subscribe in mailchimp
    merge_vars = {
          "FNAME": client.name,
          "PNAME": client.pet_name,
          "PTYPE": client.type,
    }

    if client.pricing == 29:
        merge_vars["GROUPINGS"] = [{
                    "name": "Paid",
                    "groups":["Basic"]
                }]
    elif client.pricing == 89:
        merge_vars["GROUPINGS"] = [{
                    "name": "Paid",
                    "groups":["Most Popular"]
                }]
    else:
        merge_vars["GROUPINGS"] = [{
                    "name": "Paid",
                    "groups":["Premier"]
                }]

    api = mailchimp.Mailchimp(settings.MAILCHIMP_API_KEY)
    api.lists.subscribe(settings.MAILCHIMP_LIST_ID, {"email": client.email}, merge_vars, update_existing=True)

    return redirect("/pricing")

