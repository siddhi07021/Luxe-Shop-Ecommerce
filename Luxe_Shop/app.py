import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup 
from sqlalchemy import func

app = Flask(__name__)

# 1. Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'luxe.db')
app.config['SECRET_KEY'] = 'mysecretkey'

db = SQLAlchemy(app)

# 2. Database Models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(200))
    stock = db.Column(db.Integer, default=10)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    items = db.Column(db.Text, nullable=False) 
    date_ordered = db.Column(db.DateTime, default=db.func.current_timestamp())

# 3. Custom Admin Views
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get('admin_logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

    @expose('/')
    def index(self):
        all_products = Product.query.all()
        all_orders = Order.query.all()
        
        # Chart Data
        daily_sales = db.session.query(
            func.date(Order.date_ordered).label('date'),
            func.sum(Order.total_amount).label('total')
        ).group_by('date').order_by('date').all()

        labels = [s.date for s in daily_sales]
        values = [float(s.total) for s in daily_sales]
        total_val = sum(p.price * (p.stock if p.stock else 1) for p in all_products)
        
        return self.render('admin_index.html', products=all_products, orders=all_orders, 
                           total_value=total_val, chart_labels=labels, chart_values=values)

class ProtectedModelView(ModelView):
    def is_accessible(self):
        return session.get('admin_logged_in')
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

class ProductAdminView(ProtectedModelView):
    list_template = 'admin_product_list.html'
    column_list = ('image_url', 'name', 'category', 'price', 'stock')

class OrderAdminView(ProtectedModelView):
    list_template = 'admin_order_list.html'
    column_default_sort = ('date_ordered', True)

# 4. Admin Setup
admin = Admin(app, name='LUXE | Management', index_view=MyAdminIndexView(template='admin_index.html'))
admin.base_template = 'admin_base.html'
admin.add_view(ProductAdminView(Product, db.session))
admin.add_view(OrderAdminView(Order, db.session, name="Sales Records", endpoint="order"))

# 5. Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'luxe2026':
            session['admin_logged_in'] = True
            return redirect('/admin/')
        flash('Invalid credentials.', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Successfully logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/')
def home():
    return render_template('index.html', products=Product.query.all())
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # There should be exactly 4 spaces before the line below
    app.run(host='0.0.0.0', port=5000, debug=True)