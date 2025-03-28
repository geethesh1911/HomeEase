from flask import Blueprint,render_template,request,flash,redirect,url_for,session,Response, send_file
from werkzeug.security import generate_password_hash,check_password_hash
from . import db
from sqlalchemy import func
from .models import User,ProfessionalDetails,Services,ServiceRequest,RejectedRequest
import os
import matplotlib.pyplot as plt
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from datetime import datetime
#--------------------------------------------------------
def isValidPassword(password):
    u,l,s,d=False,False,False,False
    if len(password)<8:
        return False
    for i in range(len(password)):
        if password[i].isupper():
            u=True
        elif password[i].islower():
            l=True
        elif password[i].isdigit():
            d=True
        elif password[i] in "@$!%*?&":
            s=True
    return u and l and s and d

def isValidPincode(pincode):
    return len(pincode) == 6 and pincode.isdigit()

def isValidPhone(phone_number):
    return len(phone_number)==10 and phone_number.isdigit()

#-------------------------------------------------------

auth=Blueprint('auth',__name__)


@auth.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email in ADMINS and password==ADMINS[email]:
            session['user_role']="admin"
            flash("Welcome Admin!","success")
            return redirect(url_for("auth.admin"))
        
        professional = ProfessionalDetails.query.filter_by(email=email).first()
        if professional:
            if professional.status == 'pending':
                flash("Your account is not approved by the admin yet.", "warning")
                return render_template("login.html")
            elif professional.status == 'rejected':
                flash("Your account has been rejected by the admin. Please contact support for assistance.", "danger")
                return render_template("login.html")
            if check_password_hash(professional.password, password):
                session["user_role"] = "professional"
                session["user_id"] = professional.id
                flash("Logged in successfully!", "success")
                return redirect(url_for("auth.services"))

        user=User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password,password):
            session["user_role"]="customer"
            session["user_id"]=user.id
            flash("Logged in successfully!","success")
            return redirect(url_for('auth.customer_dashboard'))
        flash("Invalid email or password", "danger")
        return render_template("login.html")
    
        
    return render_template("login.html")


#-------------------------------------------------------

@auth.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('auth.login'))

#-------------------------------------------------------

@auth.route("/customer-signup",methods=['GET','POST'])
def customer_signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone_number = request.form.get('pno')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        if not email or not password or not name or not address or not pincode:
            flash("All fields are required. Please fill in every field.", category="danger")
            return redirect(url_for('auth.customer_signup'))
        
        if not isValidPassword(password):
            flash("Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character.", category="danger")
            return redirect(url_for('auth.customer_signup'))
        
        if not isValidPincode(pincode):
            flash("Pincode must be exactly 6 digits.", category="danger")
            return redirect(url_for('auth.customer_signup'))
        
        if not isValidPhone(phone_number):
            flash("Not a valid Phone number", category="danger")
            return redirect(url_for('auth.customer_signup'))
        
        exist=User.query.filter_by(email=email).first()
        if exist:
            flash("EmailID is already in use.", category="danger")
            return redirect(url_for('auth.customer_signup'))
        
        
        hashed_password=generate_password_hash(password)

        new_customer = User(
            email=email,
            password=hashed_password,
            name=name,
            address=address,
            pincode=pincode,
            phone_number=phone_number
        )
        db.session.add(new_customer)
        db.session.commit()
        flash("Registration successful, Welcome!", category="success")
        return redirect(url_for('auth.login'))

    return render_template('customer_signup.html')


#----------------------------------------------------

@auth.route("/prof-signup",methods=['GET','POST'])
def prof_signup():
    if request.method == 'POST':
        data=request.form
        print(data)
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone_number = request.form.get('pno')
        service = request.form.get('service')
        experience = request.form.get('exp')
        address = request.form.get('address')
        pincode = request.form.get('pincode')

        if not email or not password or not name or not phone_number or not service or not experience or not address or not pincode:
            flash("All fields are required", category='error')
            return redirect(url_for('auth.prof_signup'))
        
        if service == "select":
            flash("Please select a service", category='error')
            return redirect(url_for('auth.prof_signup'))
        
        if not isValidPassword(password):
            flash("Password must be at least 8 characters long and contain uppercase, lowercase, number, and special character.", category='error')
            return redirect(url_for('auth.prof_signup'))

        if not isValidPincode(pincode):
            flash("Pincode must be exactly 6 digits.", category='error')
            return redirect(url_for('auth.prof_signup'))

        if not isValidPhone(phone_number):
            flash("Not a valid Phone number", category='error')
            return redirect(url_for('auth.prof_signup'))

        exist = ProfessionalDetails.query.filter_by(email=email).first()
        if exist:
            flash("EmailID is already in use.", category='error')
            return redirect(url_for('auth.login'))

        hashed_password = generate_password_hash(password)
        new_prof = ProfessionalDetails(
            email=email,
            password=hashed_password,  
            name=name,
            phone_number=phone_number,
            service=service,
            experience=experience,
            address=address,
            pincode=pincode
        )

        db.session.add(new_prof)
        db.session.commit()

        flash("Registration successful, Welcome!", category='success')
        return redirect(url_for('auth.login'))


    return render_template('prof-signup.html')

#-------------------------Professional routes------------------------------------

@auth.route('/services', methods=['POST', 'GET'])
def services():
    if not session.get('user_role') or session['user_role'] != 'professional':
        return redirect(url_for('auth.login'))

    professional_id = session.get('user_id')
    professional = ProfessionalDetails.query.get(professional_id)

    subquery = db.session.query(RejectedRequest.service_request_id).filter(
        RejectedRequest.professional_id == professional_id
    ).subquery()

    service_requests = ServiceRequest.query.filter(
        ServiceRequest.professional_id.is_(None),
        ServiceRequest.status == "Requested",
        ~ServiceRequest.id.in_(subquery),
        ServiceRequest.service.has(domain=professional.service)
    ).all()

    closed_requests = ServiceRequest.query.filter_by(professional_id=professional_id, status='closed').all()
    return render_template('professional_dashboard.html', service_requests=service_requests, closed_requests=closed_requests)


@auth.route('/accept_request/<int:request_id>', methods=['GET','POST'])
def accept_request(request_id):
    if 'user_role' not in session or session['user_role'] != "professional":
        flash("Please log in as a professional to accept requests", "danger")
        return redirect(url_for("auth.login"))

    professional_id = session['user_id']
    request = ServiceRequest.query.get_or_404(request_id)
    if request.status == "Requested" and request.professional_id is None:
        request.status = "accepted"
        request.professional_id = professional_id
        db.session.commit()

        flash(f"Service request {request.id} accepted", "success")
    else:
        flash(f"Service request {request.id} cannot be accepted", "danger")

    return redirect(url_for("auth.services"))
   
@auth.route('/reject_request/<int:request_id>', methods=['GET','POST'])
def reject_request(request_id):
    professional_id = session.get('user_id')
    service_request = ServiceRequest.query.get(request_id)

    if service_request:
        rejection = RejectedRequest(service_request_id=request_id, professional_id=professional_id)
        db.session.add(rejection)
        db.session.commit()
        flash("Service request rejected successfully.", "info")
    else:
        flash("Service request not found.", "danger")

    return redirect(url_for('auth.services'))

@auth.route('/close_request/<int:request_id>', methods=['POST'])
def close_request(request_id):
    if 'user_id' not in session or session.get("user_role") != "customer":
        flash("Please log in as a customer to close requests.", "danger")
        return redirect(url_for("auth.login"))

    service_request = ServiceRequest.query.get(request_id)

    if not service_request or service_request.status != "accepted":
        flash("Invalid or already closed request.", "danger")
        return redirect(url_for('auth.customer_dashboard'))

    rating = request.form.get("rating")
    remarks = request.form.get("remarks")

    if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
        flash("Rating must be a number between 1 and 5.", "danger")
        return redirect(url_for('auth.customer_dashboard'))

    service_request.rating = int(rating)
    service_request.remarks = remarks
    service_request.status = "closed"
    db.session.commit()

    flash("Service closed successfully. Thank you for your feedback!", "success")
    return redirect(url_for('auth.customer_dashboard'))


@auth.route('/professional/summary')
def professional_summary():
    print("Accessed")
    return render_template('professional_summary.html')


#--------------------------Admin routes------------------------------------------

ADMINS={
    'admin@gmail.com':'12345678'
}



@auth.route('/admin',methods=['POST','GET'])
def admin():
    services=Services.query.all()
    professionals=ProfessionalDetails.query.all()
    if not session.get('user_role'):
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        domain = request.form.get('domain')
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')

        new_service = Services(domain=domain, name=name, description=description, price=price)
        db.session.add(new_service)
        db.session.commit()

        flash("Service added successfully!", "success")
        return redirect(url_for('auth.admin'))
    return render_template('admin_dashboard.html',services=services,professionals=professionals)


@auth.route('/edit_service/<int:service_id>', methods=['POST'])
def edit_service(service_id):
    if not session.get('user_role'):
        return redirect(url_for('auth.login'))
    
    domain = request.form.get('domain')
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')

    service = Services.query.get_or_404(service_id)
    service.domain = domain
    service.name = name
    service.description = description
    service.price = price
    
    db.session.commit()

    flash("Service updated successfully!", "success")
    return redirect(url_for('auth.admin'))

@auth.route('/delete_service/<int:service_id>', methods=['POST'])
def delete_service(service_id):
    if not session.get('user_role'):
        return redirect(url_for('auth.login'))

    service = Services.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()

    flash("Service deleted successfully!", "success")
    return redirect(url_for('auth.admin'))


@auth.route('/approve_professional/<int:professional_id>')
def approve_professional(professional_id):
    professional = ProfessionalDetails.query.get_or_404(professional_id)
    professional.status = "approved"
    db.session.commit()
    flash("Professional approved successfully!", "success")
    return redirect(url_for('auth.admin'))

@auth.route('/reject_professional/<int:professional_id>')
def reject_professional(professional_id):
    professional = ProfessionalDetails.query.get_or_404(professional_id)
    professional.status = "rejected"
    db.session.commit()
    flash("Professional rejected.", "warning")
    return redirect(url_for('auth.admin'))


@auth.route('/admin/summary')
def admin_summary():
    return render_template('admin_summary.html')







#------------------------Customer Routes-----------------------------------------

@auth.route("/customer/dashboard")
def customer_dashboard():
    if 'user_role' not in session or session['user_role'] != 'customer':
        flash("You need to log in as a customer to access the dashboard.", "warning")
        return redirect(url_for("auth.login"))
    customer_id = session.get('user_id')
    current_customer=User.query.filter_by(id=customer_id).first()
    categories = ["Salon", "AC & Appliance Repair", "Cleaning & Pest Control", "Electrician", "Plumber & Carpenter"]

    service_requests = ServiceRequest.query.filter_by(customer_id=customer_id).all()

    return render_template(
        "customer_dashboard.html",
        categories=categories,
        service_requests=service_requests,
        current_customer=current_customer
    )

@auth.route("/customer/packages/<category>")
def packages(category):
    services=Services.query.filter_by(domain=category).all()
    return render_template("customer_packages.html",services=services,category=category)

@auth.route('/customer/book_service/<int:service_id>', methods=['POST', 'GET'])
def book_service(service_id):
    if 'user_id' not in session or session.get("user_role") != "customer":
        flash("Please log in as a customer to book services", "danger")
        return redirect(url_for("auth.login"))

    customer_id = session['user_id']
    new_request = ServiceRequest(service_id=service_id, customer_id=customer_id, status="Requested")
    db.session.add(new_request)
    db.session.commit()
    return redirect(url_for("auth.customer_dashboard"))

@auth.route('/customer/summary')
def customer_summary():
    return render_template('customer_summary.html')






#--------------------------------------Summaries----------------------------------------------------

@auth.route('/professional/summary/service_requests')
def service_requests_graph():
    professional_id = session.get('user_id')  
    if not professional_id:
        flash("You are not logged in as a professional.", "danger")
        return redirect(url_for('auth.professional_dashboard'))

    closed_count = db.session.query(ServiceRequest).filter_by(professional_id=professional_id, status="closed").count()

    rejected_count = db.session.query(RejectedRequest).filter_by(professional_id=professional_id).count()

    received_count = db.session.query(ServiceRequest).filter_by(professional_id=professional_id).count()

    labels = ['Received', 'Closed', 'Rejected']
    sizes = [received_count, closed_count, rejected_count]
    colors = ['#4CAF50', '#FF9800', '#F44336']

    fig, ax = plt.subplots()
    ax.bar(labels, sizes, color=colors)
    ax.set_title('Service Requests Summary')
    ax.set_ylabel('Count')

    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)

    return send_file(img, mimetype='image/png')


@auth.route('/professional/summary/ratings')
def ratings_distribution_graph():
    professional_id = session.get('user_id')
    if not professional_id:
        flash("You are not logged in as a professional.", "danger")
        return redirect(url_for('auth.professional_dashboard'))

    ratings = (
        db.session.query(ServiceRequest.rating)
        .filter(
            ServiceRequest.professional_id == professional_id,
            ServiceRequest.rating.isnot(None)
        )
        .all()
    )

    rating_counts = {rating: 0 for rating in range(1, 6)}
    for (rating,) in ratings:
        rating_counts[rating] += 1

    labels = list(rating_counts.keys())
    sizes = list(rating_counts.values())
    colors = ['#66b3ff', '#ff9999', '#99ff99', '#ffcc99', '#c2c2f0']

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    ax.set_title('Ratings Distribution')
    ax.axis('equal') 

    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)

    return send_file(img, mimetype='image/png')



@auth.route('/customer/summary/service_requests')
def customer_service_requests_graph():
    customer_id = session.get('user_id')  

    requested_count = db.session.query(ServiceRequest).filter_by(customer_id=customer_id, status="Requested").count()
    closed_count = db.session.query(ServiceRequest).filter_by(customer_id=customer_id, status="closed").count()
    assigned_count = db.session.query(ServiceRequest).filter_by(customer_id=customer_id, status="accepted").count()

    labels = ['Requested', 'Closed', 'Assigned']
    sizes = [requested_count, closed_count, assigned_count]
    colors = ['#2196F3', '#4CAF50', '#FFC107']

    fig, ax = plt.subplots()
    ax.bar(labels, sizes, color=colors)
    ax.set_title('Service Requests Summary (Customer)')
    ax.set_ylabel('Count')

    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)

    return send_file(img, mimetype='image/png')


@auth.route('/admin/overall_customer_ratings')
def overall_customer_ratings():
    ratings_count = db.session.query(ServiceRequest.rating, db.func.count(ServiceRequest.rating)) \
        .group_by(ServiceRequest.rating).all()

    labels = [str(rating) + " Stars" for rating, _ in ratings_count]
    sizes = [count for _, count in ratings_count]
    colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0']  

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, colors=colors[:len(sizes)], autopct="%1.1f%%", startangle=90)
    ax.axis('equal')

    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    fig.savefig(img)
    img.seek(0)

    return send_file(img, mimetype='image/png')

@auth.route('/admin/service_requests_summary')
def service_requests_summary():
    requested_count = db.session.query(ServiceRequest).filter_by(status="Requested").count()
    closed_count = db.session.query(ServiceRequest).filter_by(status="closed").count()
    assigned_count = db.session.query(ServiceRequest).filter_by(status="accepted").count()

    labels = ['Requested', 'Closed', 'Assigned']
    sizes = [requested_count, closed_count, assigned_count]
    colors = ['#4CAF50', '#FF9800', '#F44336']

    fig, ax = plt.subplots()
    ax.bar(labels, sizes, color=colors)
    ax.set_title('Service Requests Summary')
    ax.set_ylabel('Count')

    canvas = FigureCanvas(fig)
    img = io.BytesIO()
    fig.savefig(img)
    img.seek(0)

    return send_file(img, mimetype='image/png')



#----------------------------------------Search functionalities------------------------------------------------


@auth.route('/customer/search', methods=['GET'])
def search_services():
    search_by = request.args.get('search_by') 
    search_value = request.args.get('search_value')  

    query = db.session.query(Services).join(ServiceRequest, isouter=True)

    if search_by == 'domain' and search_value:
        query = query.filter(Services.domain.ilike(f'%{search_value}%'))
    elif search_by == 'name' and search_value:
        query = query.filter(Services.name.ilike(f'%{search_value}%'))
    elif search_by == 'rating' and search_value:
        try:
            rating_value = int(search_value)
            query = query.filter(ServiceRequest.rating == rating_value)
        except ValueError:
            return render_template('customer_search.html', error="Invalid rating value.")
    elif search_by == 'price' and search_value:
        try:
            price_value = float(search_value)
            query = query.filter(Services.price <= price_value)  
        except ValueError:
            return render_template('customer_search.html', error="Invalid price value.")

    services = query.add_columns(
        func.avg(ServiceRequest.rating).label('average_rating')
    ).group_by(Services.id).all()

    services_with_avg_rating = []
    for service, avg_rating in services:
        service.average_rating = avg_rating
        services_with_avg_rating.append(service)

    return render_template('customer_search.html', services=services_with_avg_rating)


@auth.route('/professional/search', methods=['GET'])
def search_professional_requests():
    
    professional_id = session.get('user_id') 
    
    if not professional_id:
        return redirect(url_for('auth.login')) 

    search_by = request.args.get('search_by')  
    search_value = request.args.get('search_value') 

    query = db.session.query(
        ServiceRequest.id,
        User.name.label("customer_name"),
        User.phone_number.label("contact_phone"),
        User.address.label("address"),
        User.pincode.label("pincode"),
        ServiceRequest.date_created.label("date_closed"),
        ServiceRequest.rating
    ).join(ServiceRequest.customer)\
     .filter(ServiceRequest.professional_id == professional_id, ServiceRequest.status == 'closed')

    if search_by == 'customer_name' and search_value:
        query = query.filter(User.name.ilike(f'%{search_value}%'))
    elif search_by == 'pincode' and search_value:
        query = query.filter(User.pincode.ilike(f'%{search_value}%'))
    elif search_by == 'date_closed' and search_value:
        try:
            closed_date = datetime.strptime(search_value, '%Y-%m-%d').date()
            query = query.filter(ServiceRequest.date_created <= closed_date)
        except ValueError:
            return render_template('professional_search.html', error="Please provide a valid date in YYYY-MM-DD format.")
    elif search_by == 'rating' and search_value:
        if search_value.isdigit():
            rating_value = int(search_value)
            query = query.filter(ServiceRequest.rating == rating_value)
        else:
            return render_template('professional_search.html', error="Please provide a valid rating value (integer).")

    service_requests = query.all()

    return render_template('professional_search.html', service_requests=service_requests)



@auth.route('/admin/search-service-requests', methods=['GET'])
def search_admin_requests():
    search_by = request.args.get('search_by')
    search_value = request.args.get('search_value')

    query = db.session.query(ServiceRequest).join(User, User.id == ServiceRequest.customer_id) \
                                              .join(ProfessionalDetails, ProfessionalDetails.id == ServiceRequest.professional_id) \
                                              .join(Services, Services.id == ServiceRequest.service_id)
    
    if search_by == 'service_name' and search_value:
        query = query.filter(Services.name.ilike(f'%{search_value}%'))
    elif search_by == 'professional_name' and search_value:
        query = query.filter(ProfessionalDetails.name.ilike(f'%{search_value}%'))
    elif search_by == 'customer_name' and search_value:
        query = query.filter(User.name.ilike(f'%{search_value}%'))
    elif search_by == 'date_created' and search_value:
        try:
            date = datetime.strptime(search_value, '%Y-%m-%d')
            query = query.filter(ServiceRequest.date_created == date)
        except ValueError:
            return render_template('admin_search.html', error="Invalid date format. Use YYYY-MM-DD.")

    service_requests = query.all()
    return render_template('admin_search.html', service_requests=service_requests)



#-------------------------------------------Profiles----------------------------------------------------------------

@auth.route('/professional/profile')
def professional_profile():
    professional_id = session.get('user_id')
    print(professional_id)
    if not professional_id:
        flash("Please log in to access your profile.", "warning")
        return redirect(url_for('auth.login'))

    professional = ProfessionalDetails.query.get(professional_id)
    if not professional:
        flash("Professional not found.", "danger")
        return redirect(url_for('auth.login'))

    closed_requests = ServiceRequest.query.filter_by(professional_id=professional_id, status="closed").all()
    
    total_rating = sum(req.rating for req in closed_requests if req.rating is not None)
    completed_requests = len(closed_requests)
    average_rating = total_rating / completed_requests if completed_requests > 0 else None

    return render_template(
        'professional_profile.html',
        professional=professional,
        total_rating=total_rating,
        completed_requests=completed_requests,
        average_rating=average_rating
    )


@auth.route('/customer/profile')
def customer_profile():
    customer_id = session.get('user_id')
    customer = User.query.get(customer_id)

    return render_template('customer_profile.html', customer=customer)

















