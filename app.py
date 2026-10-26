from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import qrcode
import io
import os
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'lablink-secret-key-prototype-v2')

# ── Database Configuration ──────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "lablink.db")}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── SQLAlchemy Models ───────────────────────────────────────
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='student')
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class Equipment(db.Model):
    __tablename__ = 'equipment'

    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Available')
    condition = db.Column(db.String(50), nullable=False, default='Good')
    student = db.Column(db.String(50), default='', nullable=True)
    due = db.Column(db.String(50), default='', nullable=True)
    photo = db.Column(db.String(255), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    specs = db.Column(db.JSON, default=dict)
    cost = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    vendor = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.String(50), nullable=True)
    total_qty = db.Column(db.Integer, default=10)
    available_qty = db.Column(db.Integer, default=10)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'location': self.location,
            'status': self.status,
            'condition': self.condition,
            'student': self.student or '',
            'due': self.due or '',
            'photo': self.photo or '',
            'model': self.model or '',
            'specs': self.specs or {},
            'cost': self.cost or 0,
            'description': self.description or '',
            'vendor': self.vendor or '',
            'purchase_date': self.purchase_date or '',
            'total_qty': self.total_qty,
            'available_qty': self.available_qty
        }

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class BorrowRequest(db.Model):
    __tablename__ = 'borrow_requests'

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), db.ForeignKey('equipment.id'), nullable=False)
    equipment_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)
    purpose = db.Column(db.String(255), nullable=True)
    due = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(50), default='Pending')

    @property
    def equipment(self):
        return self.equipment_name

    @equipment.setter
    def equipment(self, value):
        self.equipment_name = value

    @property
    def student(self):
        return self.student_id

    @student.setter
    def student(self, value):
        self.student_id = value

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class HistoryEntry(db.Model):
    __tablename__ = 'history_entries'

    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.String(50), db.ForeignKey('equipment.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    time = db.Column(db.String(50), nullable=False)

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


# ── Seed Data Definitions ────────────────────────────────────
SEED_USERS = [
    {
        'username': 'student',
        'password_hash': generate_password_hash('student123'),
        'role': 'student',
        'name': 'Student Demo',
        'email': 'student@college.edu'
    },
    {
        'username': 'tech',
        'password_hash': generate_password_hash('tech123'),
        'role': 'technician',
        'name': 'Technician Demo',
        'email': 'tech@college.edu'
    },
    {
        'username': 'faculty',
        'password_hash': generate_password_hash('faculty123'),
        'role': 'faculty',
        'name': 'Faculty Demo',
        'email': 'faculty@college.edu'
    }
]

SEED_EQUIPMENT = [
    {
        'id': 'SG-001',
        'name': 'Screw Gauge',
        'category': 'Measuring Instrument',
        'location': 'Physics Lab',
        'status': 'Available',
        'condition': 'Good',
        'student': '',
        'due': '',
        'total_qty': 10,
        'available_qty': 10,
        'photo': 'images/equip/SG-001.jpg',
        'model': 'SG-25-PRE',
        'specs': {
            'Range': '0–25 mm',
            'Pitch': '0.5 mm',
            'Least Count': '0.01 mm',
            'Accuracy': '±0.004 mm',
            'Material': 'Hardened Tool Steel'
        },
        'cost': 850,
        'description': 'Precision micrometer screw gauge used for accurate external diameter and thickness measurements of wires, thin rods, and metal plates in fundamental physics experiments.',
        'vendor': 'Apex Scientific Instruments',
        'purchase_date': '2024-03-15'
    },
    {
        'id': 'VC-002',
        'name': 'Vernier Caliper',
        'category': 'Measuring Instrument',
        'location': 'Physics Lab',
        'status': 'Issued',
        'condition': 'Good',
        'student': '23CSE014',
        'due': '2026-11-15',
        'total_qty': 8,
        'available_qty': 7,
        'photo': 'images/equip/VC-002.jpg',
        'model': 'VC-150-SS',
        'specs': {
            'Range': '0–150 mm',
            'Resolution': '0.02 mm',
            'Accuracy': '±0.03 mm',
            'Jaws': 'Internal & External with Depth Rod',
            'Material': 'Stainless Steel'
        },
        'cost': 1400,
        'description': 'Dual-scale metric and imperial vernier caliper for measuring internal dimensions, external dimensions, and stepped depths with high precision.',
        'vendor': 'Precision Tools Ltd.',
        'purchase_date': '2024-01-20'
    },
    {
        'id': 'DM-003',
        'name': 'Digital Multimeter',
        'category': 'Electrical Instrument',
        'location': 'Electronics Lab',
        'status': 'Available',
        'condition': 'Good',
        'student': '',
        'due': '',
        'total_qty': 6,
        'available_qty': 6,
        'photo': 'images/equip/DM-003.jpg',
        'model': 'Fluke 101 Pocket DMM',
        'specs': {
            'DC Voltage': '600 V max',
            'AC Voltage': '600 V max',
            'Resistance': '40 MΩ max',
            'Display': '6000 Count LCD',
            'Safety Rating': 'CAT III 600V'
        },
        'cost': 3200,
        'description': 'Compact true-RMS digital multimeter for testing electronic circuits, checking continuity, and measuring DC/AC voltage, current, and component resistances.',
        'vendor': 'Fluke India Corp.',
        'purchase_date': '2023-08-10'
    },
    {
        'id': 'OS-004',
        'name': 'Oscilloscope',
        'category': 'Electronic Instrument',
        'location': 'Electronics Lab',
        'status': 'Under Maintenance',
        'condition': 'Needs service',
        'student': '',
        'due': '',
        'total_qty': 2,
        'available_qty': 0,
        'photo': 'images/equip/OS-004.jpg',
        'model': 'TBS1052B-EDU',
        'specs': {
            'Bandwidth': '50 MHz',
            'Channels': '2 Analog Channels',
            'Sample Rate': '1.0 GS/s',
            'Record Length': '2.5k points',
            'Display': '7-inch Color WVGA TFT'
        },
        'cost': 38500,
        'description': 'Digital storage oscilloscope designed for laboratory signal analysis, waveform visualization, frequency response characterization, and debugging electronic circuits.',
        'vendor': 'Tektronix India',
        'purchase_date': '2022-11-05'
    },
    {
        'id': 'PS-005',
        'name': 'DC Power Supply',
        'category': 'Electrical Instrument',
        'location': 'Electronics Lab',
        'status': 'Overdue',
        'condition': 'Good',
        'student': '23ECE009',
        'due': '2026-09-19',
        'total_qty': 4,
        'available_qty': 3,
        'photo': 'images/equip/PS-005.jpg',
        'model': 'GPS-3030DD',
        'specs': {
            'Output Voltage': '0–30 V DC',
            'Output Current': '0–3 A',
            'Display': 'Dual 3-Digit Digital LED',
            'Regulation': 'CV ≤ 0.01% + 3mV',
            'Power Rating': '180 W'
        },
        'cost': 11200,
        'description': 'Regulated linear benchtop DC power supply with dual adjustable outputs, constant current and constant voltage modes, overload protection, and current limiting.',
        'vendor': 'Good Will Instrument Co.',
        'purchase_date': '2023-04-12'
    }
]


# ── Database Initialization & Seeding ────────────────────────
def seed_database():
    """Seed the database with default users and equipment if empty."""
    if User.query.first() is None:
        for u in SEED_USERS:
            user = User(
                username=u['username'],
                password_hash=u['password_hash'],
                role=u['role'],
                name=u['name'],
                email=u['email']
            )
            db.session.add(user)
        db.session.commit()

    if Equipment.query.first() is None:
        for e in SEED_EQUIPMENT:
            equip = Equipment(
                id=e['id'],
                name=e['name'],
                category=e['category'],
                location=e['location'],
                status=e['status'],
                condition=e['condition'],
                student=e.get('student', ''),
                due=e.get('due', ''),
                total_qty=e.get('total_qty', 10),
                available_qty=e.get('available_qty', 10),
                photo=e.get('photo', ''),
                model=e.get('model', ''),
                specs=e.get('specs', {}),
                cost=e.get('cost', 0),
                description=e.get('description', ''),
                vendor=e.get('vendor', ''),
                purchase_date=e.get('purchase_date', '')
            )
            db.session.add(equip)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_database()


# ── Helpers & Decorators ─────────────────────────────────────
def refresh_status():
    """Synchronize equipment statuses based on availability and due dates."""
    today = date.today().isoformat()
    equipment_items = Equipment.query.all()
    changed = False

    for e in equipment_items:
        avail = e.available_qty or 0
        status = e.status
        if status == 'All Issued' and avail > 0:
            e.status = 'Available'
            changed = True
        elif status == 'Available' and avail == 0:
            e.status = 'All Issued'
            changed = True

        if e.status == 'Issued' and e.due and e.due < today:
            e.status = 'Overdue'
            changed = True
        elif e.status == 'Overdue' and e.due and e.due >= today:
            e.status = 'Issued'
            changed = True

    if changed:
        db.session.commit()


def log_history(eid, action, detail=''):
    """Record an audit trail entry for an equipment record."""
    entry = HistoryEntry(
        equipment_id=eid,
        action=action,
        detail=detail,
        time=datetime.now().strftime('%Y-%m-%d %H:%M')
    )
    db.session.add(entry)
    db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login', next=request.url))
            user_role = session['user'].get('role')
            if user_role not in allowed_roles:
                flash(f"Access restricted. Role '{user_role}' does not have permission.", 'error')
                return redirect(url_for('student' if user_role == 'student' else 'index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ── Authentication Routes ────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if user and user.check_password(password):
            session['user'] = {
                'username': user.username,
                'name': user.name or user.username,
                'role': user.role or 'student',
                'email': user.email or ''
            }
            flash(f"Welcome back, {session['user']['name']}!", 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            if session['user']['role'] in ['technician', 'faculty']:
                return redirect(url_for('admin'))
            return redirect(url_for('student'))

        flash('Invalid username or password. Please try again.', 'error')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student').strip().lower()

        # Faculty self-signup is forbidden
        if role not in ['student', 'technician']:
            flash('Invalid role selected. Self-registration is allowed for Students and Technicians only.', 'error')
            return render_template('signup.html')

        if not username or not password or not name:
            flash('All required fields must be filled out.', 'error')
            return render_template('signup.html')

        if User.query.filter(db.func.lower(User.username) == username.lower()).first():
            flash(f"Username '{username}' is already taken. Please choose another.", 'error')
            return render_template('signup.html')

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
            name=name,
            email=email
        )
        db.session.add(new_user)
        db.session.commit()

        session['user'] = {
            'username': new_user.username,
            'name': new_user.name,
            'role': new_user.role,
            'email': new_user.email or ''
        }
        flash('Account registered successfully! Welcome to TCELABLINK.', 'success')
        return redirect(url_for('admin' if role == 'technician' else 'student'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('index'))


# ── QR Code Generator (Public) ───────────────────────────────
BASE_URL = None

@app.route('/qr/<eid>.png')
def qr_image(eid):
    e = db.session.get(Equipment, eid)
    if not e:
        return ('Not found', 404)
    if BASE_URL:
        url = f"{BASE_URL}/equipment/{eid}"
    else:
        url = url_for('details', eid=eid, _external=True)
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return app.response_class(buf.getvalue(), mimetype='image/png')


# ── Public Pages ─────────────────────────────────────────────
@app.route('/')
def index():
    refresh_status()
    equipment_list = Equipment.query.all()
    c = {
        'total': len(equipment_list),
        'available': sum(1 for e in equipment_list if e.status == 'Available'),
        'issued': sum(1 for e in equipment_list if e.status == 'Issued'),
        'attention': sum(1 for e in equipment_list if e.status in ['Overdue', 'Defective', 'Under Maintenance']),
        'overdue': sum(1 for e in equipment_list if e.status == 'Overdue'),
        'maintenance': sum(1 for e in equipment_list if e.status == 'Under Maintenance')
    }
    return render_template('index.html', counts=c, equipment=equipment_list)


# ── Authenticated User Pages ─────────────────────────────────
@app.route('/student')
@login_required
def student():
    refresh_status()
    equipment_list = Equipment.query.all()
    return render_template('student.html', equipment=equipment_list)


@app.route('/equipment/<eid>')
@login_required
def details(eid):
    e = db.session.get(Equipment, eid)
    if not e:
        return ('Not found', 404)
    history_entries = HistoryEntry.query.order_by(HistoryEntry.id.asc()).all()
    return render_template('equipment.html', item=e, history=history_entries)


@app.route('/request/<eid>', methods=['GET', 'POST'])
@login_required
def borrow(eid):
    user_role = session.get('user', {}).get('role')
    if user_role not in ['student', 'technician']:
        flash('Faculty accounts are read-only. Borrow requests can only be placed by students.', 'error')
        return redirect(url_for('details', eid=eid))

    e = db.session.get(Equipment, eid)
    if not e:
        return ('Not found', 404)

    if request.method == 'POST':
        sid = request.form.get('student_id', '').strip()
        due = request.form.get('due_date', '').strip()
        purpose = request.form.get('purpose', 'Academic Project').strip()

        new_req = BorrowRequest(
            equipment_id=eid,
            equipment_name=e.name,
            student_id=sid,
            purpose=purpose,
            due=due,
            status='Pending'
        )
        db.session.add(new_req)
        log_history(eid, 'Requested', f'Request by {sid} for {purpose}')
        db.session.commit()
        flash(f'Borrow request submitted for {e.name}.', 'success')
        return render_template('success.html', item=e, student_id=sid)

    return render_template('request.html', item=e)


# ── Staff Admin Pages ────────────────────────────────────────
@app.route('/admin')
@role_required('technician', 'faculty')
def admin():
    refresh_status()
    equipment_list = Equipment.query.all()
    requests_list = BorrowRequest.query.order_by(BorrowRequest.id.desc()).all()
    recent_history = HistoryEntry.query.order_by(HistoryEntry.id.desc()).limit(10).all()
    return render_template(
        'admin.html',
        equipment=equipment_list,
        requests=requests_list,
        recent_history=recent_history,
        current_role=session.get('user', {}).get('role')
    )


@app.route('/admin/qr/<eid>')
@role_required('technician', 'faculty')
def admin_qr(eid):
    e = db.session.get(Equipment, eid)
    if not e:
        flash('Equipment not found.', 'error')
        return redirect(url_for('admin'))
    return render_template('admin_qr.html', item=e)


@app.post('/admin/issue/<eid>')
@role_required('technician', 'faculty')
def issue(eid):
    if session.get('user', {}).get('role') != 'technician':
        flash('Permission denied. Faculty accounts are read-only; only technicians can issue equipment.', 'error')
        return redirect(url_for('admin'))

    e = db.session.get(Equipment, eid)
    if e:
        if (e.available_qty or 0) < 1:
            flash('No units available', 'error')
            return redirect(url_for('admin'))

        sid = request.form.get('student_id', '').strip()
        due = request.form.get('due_date', '').strip()

        e.available_qty = (e.available_qty or 0) - 1
        if e.available_qty == 0:
            e.status = 'All Issued'

        if sid:
            e.student = sid
        if due:
            e.due = due

        # Update matching pending request if present
        pending_req = BorrowRequest.query.filter_by(equipment_id=eid, status='Pending').first()
        if pending_req:
            pending_req.status = 'Issued'

        log_history(eid, 'Issued', f"Issued 1 unit. Remaining: {e.available_qty}/{e.total_qty}")
        db.session.commit()
        flash(f'{e.name} ({eid}) issued to {sid}.', 'success')
    return redirect(url_for('admin'))


@app.post('/admin/return/<eid>')
@role_required('technician', 'faculty')
def ret(eid):
    if session.get('user', {}).get('role') != 'technician':
        flash('Permission denied. Faculty accounts are read-only; only technicians can confirm returns.', 'error')
        return redirect(url_for('admin'))

    e = db.session.get(Equipment, eid)
    if e:
        total = e.total_qty or 10
        if (e.available_qty or 0) < total:
            e.available_qty = (e.available_qty or 0) + 1

        if e.status == 'All Issued':
            e.status = 'Available'

        if e.available_qty == total:
            e.student = ''
            e.due = ''

        # Update matching issued request if present
        issued_req = BorrowRequest.query.filter_by(equipment_id=eid, status='Issued').first()
        if issued_req:
            issued_req.status = 'Returned'

        log_history(eid, 'Returned', f"Returned 1 unit. Remaining: {e.available_qty}/{e.total_qty}")
        db.session.commit()
        flash(f'Return confirmed for {e.name} ({eid}).', 'success')
    return redirect(url_for('admin'))


@app.post('/admin/defective/<eid>')
@role_required('technician', 'faculty')
def mark_defective(eid):
    if session.get('user', {}).get('role') != 'technician':
        flash('Permission denied. Faculty accounts are read-only.', 'error')
        return redirect(url_for('admin'))

    e = db.session.get(Equipment, eid)
    if e:
        e.status = 'Defective'
        e.condition = 'Needs inspection'
        e.student = ''
        e.due = ''
        log_history(eid, 'Marked Defective', 'Flagged for inspection')
        db.session.commit()
        flash(f'{e.name} ({eid}) marked as defective.', 'warning')
    return redirect(url_for('admin'))


@app.post('/admin/maintenance/<eid>')
@role_required('technician', 'faculty')
def mark_maintenance(eid):
    if session.get('user', {}).get('role') != 'technician':
        flash('Permission denied. Faculty accounts are read-only.', 'error')
        return redirect(url_for('admin'))

    e = db.session.get(Equipment, eid)
    if e:
        e.status = 'Under Maintenance'
        e.condition = 'Under service'
        e.student = ''
        e.due = ''
        log_history(eid, 'Sent to Maintenance', 'Out for servicing')
        db.session.commit()
        flash(f'{e.name} ({eid}) moved to maintenance.', 'warning')
    return redirect(url_for('admin'))


@app.post('/admin/restore/<eid>')
@role_required('technician', 'faculty')
def restore(eid):
    if session.get('user', {}).get('role') != 'technician':
        flash('Permission denied. Faculty accounts are read-only.', 'error')
        return redirect(url_for('admin'))

    e = db.session.get(Equipment, eid)
    if e:
        e.status = 'Available'
        e.condition = 'Good'
        e.student = ''
        e.due = ''
        log_history(eid, 'Restored', 'Back in service')
        db.session.commit()
        flash(f'{e.name} ({eid}) restored to Available condition.', 'success')
    return redirect(url_for('admin'))


# ── JSON API (Public) ────────────────────────────────────────
@app.route('/api/equipment/<eid>')
def api(eid):
    e = db.session.get(Equipment, eid)
    return jsonify(e.to_dict() if e else {'error': 'not found'}), 404 if not e else 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
