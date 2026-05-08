from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
import requests

from werkzeug.utils import secure_filename
from pypdf import PdfReader

app = Flask(__name__)

app.secret_key = 'supersecretkey'

# 🔹 Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@db:5432/portfoliodb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# =========================
# ✅ ADD MODELS HERE
# =========================

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))
    # Relationship (optional but recommended)
    skills = db.relationship('Skill', backref='project', lazy=True)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))
    extracted_text = db.Column(db.Text)

from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# =========================
# ROUTES BELOW
# =========================

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '1234':
            session['admin'] = True
            return redirect(request.args.get('next') or url_for('projects'))

        return "Invalid credentials"

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

@app.route('/projects')
def projects():
    projects = Project.query.all()
    return render_template('projects.html', projects=projects)

@app.route('/add-project', methods=['GET', 'POST'])
@admin_required
def add_project():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        skills_input = request.form['skills']  # comma separated

        # Create project
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()  # commit first to get project.id

        # Add skills
        skills_list = skills_input.split(',')

        for skill_name in skills_list:
            skill = Skill(
                name=skill_name.strip(),
                project_id=project.id
            )
            db.session.add(skill)

        db.session.commit()

        return redirect(url_for('projects'))

    return render_template('add_project.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        return f"Thanks {name}, we got your email!"

    return render_template('contact.html')

@app.route('/edit-project/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_project(id):
    project = Project.query.get_or_404(id)

    if request.method == 'POST':
        project.name = request.form['name']
        project.description = request.form['description']

        # Clear old skills
        Skill.query.filter_by(project_id=project.id).delete()

        # Add updated skills
        skills_input = request.form['skills']
        if skills_input:
            skills_list = skills_input.split(',')

            for skill_name in skills_list:
                if skill_name.strip():
                    skill = Skill(
                        name=skill_name.strip(),
                        project_id=project.id
                    )
                    db.session.add(skill)

        db.session.commit()

        return redirect(url_for('projects'))

    # Pre-fill skills
    skills = ', '.join([skill.name for skill in project.skills])

    return render_template('edit_project.html', project=project, skills=skills)

@app.route('/delete-project/<int:id>')
@admin_required
def delete_project(id):
    project = Project.query.get_or_404(id)

    db.session.delete(project)
    db.session.commit()

    return redirect(url_for('projects'))

@app.route('/upload-resume', methods=['GET', 'POST'])
@admin_required
def upload_resume():

    if request.method == 'POST':

        file = request.files['resume']

        if file:

            filename = secure_filename(file.filename)

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(filepath)

            # Extract PDF text
            reader = PdfReader(filepath)

            text = ""

            for page in reader.pages:

                extracted = page.extract_text()

                if extracted:
                    text += extracted

            # Save to DB
            resume = Resume(
                filename=filename,
                extracted_text=text
            )

            db.session.add(resume)
            db.session.commit()

            return redirect(url_for('analyze_resume', id=resume.id))

    return render_template('upload_resume.html')

@app.route('/analyze-resume/<int:id>')
@admin_required
def analyze_resume(id):

    resume = Resume.query.get_or_404(id)

    prompt = f"""
    Analyze this resume.

    Extract:
    - Technical skills
    - Experience level
    - Best matching job roles
    - Missing technologies
    - Career improvement suggestions

    Resume:
    {resume.extracted_text}
    """

    response = requests.post(
        "http://172.26.171.196:11434/api/generate",
        json={
            "model": "phi3",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    print(data)

    analysis = data.get("response", "No AI response generated")

    return render_template(
        'resume_analysis.html',
        analysis=analysis
    )
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
