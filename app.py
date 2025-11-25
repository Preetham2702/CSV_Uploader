from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash,send_file
import smtplib
import random
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
load_dotenv()
from werkzeug.utils import secure_filename
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cv2
import csv
import numpy as np
import imageio
from uuid import uuid4
import io
from PIL import Image
from datetime import datetime
from itertools import islice
from math import ceil



app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")
ACCESS_PIN = os.getenv("ACCESS_PIN")

otp_store = {}

UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5 GB
os.environ["IMAGEIO_FFMPEG_EXE"] = "/opt/homebrew/bin/ffmpeg"

# hostname = os.getenv("DB_HOST")
# database = os.getenv("DB_NAME")
# username = os.getenv("DB_USER")
# pwd = os.getenv("DB_PASSWORD")
# port_id = os.getenv("DB_PORT")

#for supabase
username = os.getenv("user")
pwd = os.getenv("password")
hostname = os.getenv("host")
port_id = os.getenv("port")
database = os.getenv("dbname")


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def landing():
    return render_template('landing.html')

@app.route('/request_access', methods=['POST'])
def request_access():
    return redirect(url_for('enter_otp'))

# OTP Entry Page
@app.route('/enter_pin', methods=['GET', 'POST'])
def enter_pin():
    if request.method == 'POST':
        entered_pin = request.form.get('pin')
        if entered_pin == ACCESS_PIN:
            session['authenticated'] = True
            return redirect(url_for('home'))  # or main_page
        return render_template('pin.html', error="Invalid Access Code.")
    return render_template('pin.html')

@app.route('/verify_pin', methods=['POST'])
def verify_pin():
    pin = ''.join([request.form.get(f'digit{i}', '') for i in range(4)])
    if pin == ACCESS_PIN:
        session['authenticated'] = True
        return redirect(url_for('main_page'))  # Or your secured route
    else:
        return render_template('landing.html', error="Incorrect PIN")

# Dashboard Page
@app.route('/main_page')
def main_page():
    if not session.get('authenticated'):
        return redirect(url_for('landing'))
    return render_template('main.html')

# Logout (optional)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))


@app.route('/handle_stage_selection', methods=['POST'])
def handle_stage_selection():
    stage = request.form['stage']

    if stage == 'in_process':
        return redirect(url_for('select_sensor'))
    elif stage == 'design_stage':
        return redirect(url_for('enter_details', stage='design_stage'))
    elif stage == 'post_process':
        return redirect(url_for('enter_details', stage='post_process'))
    else:
        return "Invalid selection"

@app.route('/select_sensor', methods=['GET', 'POST'])
def select_sensor():
    return render_template('select_sensor.html')

@app.route('/handle_sensor_selection', methods=['POST'])
def handle_sensor_selection():
    sensor = request.form.get('sensor')

    if sensor == 'sensor1':
        return "Sensor 1 page coming soon."
    elif sensor == 'sensor2':
        return "Sensor 2 page coming soon."
    elif sensor == 'sensor3':
        return redirect(url_for('sensor3_subtype', sensor = 'sensor3'))

    if sensor == 'pico_log':
        session['stage'] = 'pico_log'
        return redirect(url_for('enter_details', stage ='pico_log'))
    else:
        return "Invalid sensor"

@app.route('/sensor3_subtype', methods=['GET', 'POST'])
def sensor3_subtype():
    return render_template('sensor3.html')

@app.route('/handle_sensor3_type', methods=['POST'])
def handle_sensor3_type():
    subtype = request.form['type']

    if subtype == 'ircamera':
        return redirect(url_for('enter_details', stage='ircamera'))
    elif subtype == 'tdvideo':
        return "tdvedio page comming soon"
    elif subtype == 'tdimage':
        return "tdimage page comming soon"
    else:
        return "Invalid sensor3 subtype"

@app.route('/operator', methods=['GET', 'POST'])
def operator():
    stage = request.args.get('stage') or request.form.get('stage')
    operators = []

    conn = None
    cur  = None

    try:
        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur = conn.cursor()

        if request.method == 'POST':
            operator_id = int(request.form['operator_id'])
            operator_name = request.form['operator_name']

            try:
                cur.execute("INSERT INTO operators (operator_id, operator_name) VALUES (%s, %s)", (operator_id, operator_name,))
                conn.commit()

            except Exception as e:
                return f"Error inserting values {e}"

        # Load operator table to show in the table:
        cur.execute("SELECT operator_id, operator_name FROM operators")
        operators = cur.fetchall()

    except Exception as e:
        return f"Error table not existing {e}"
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    return render_template('operator.html', operators=operators, stage=stage)

@app.route('/machine', methods=['GET', 'POST'])
def machine():
    stage = request.args.get('stage') or request.form.get('stage')
    machines = []

    try:
        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur = conn.cursor()

        if request.method == 'POST':
            machine_id = int(request.form['machine_id'])
            machine_name = request.form['machine_name']
            # store in session
            session['machine_id'] = machine_id

            try:
                cur.execute("INSERT INTO machines (machine_id, machine_name) VALUES (%s, %s)", (machine_id, machine_name,))
                conn.commit()

            except Exception as e:
                return f"Error inserting values {e}"

        # Load operator table to show in the table:
        cur.execute("SELECT machine_id, machine_name FROM machines")
        machines = cur.fetchall()

    except Exception as e:
        return f"Error table not existing {e}"
    finally:
        cur.close()
        conn.close()

    return render_template('machine.html', machines=machines, stage=stage)

@app.route('/add_material', methods=['GET', 'POST'])
def add_material():
    stage = request.args.get('stage') or request.form.get('stage')
    materials= []
    try:
        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur = conn.cursor()

        if request.method == 'POST':
            material_id = int(request.form['material_id'])
            material_name = request.form['material_name']

            try:
                cur.execute("INSERT INTO materials (material_id, material_name) VALUES (%s, %s)", (material_id, material_name,))
                conn.commit()

            except Exception as e:
                return f"Error inserting values {e}"


            # Load material table to show in the table:
        cur.execute("SELECT material_id, material_name FROM materials")
        materials = cur.fetchall()

    except Exception as e:
        return f"Error table not existing {e}"
    finally:
        cur.close()
        conn.close()

    return render_template('add_material.html', materials=materials, stage=stage)

@app.route('/add_deposits', methods=['GET', 'POST'])
def add_deposits():
    stage = request.values.get('stage')  # works for GET & POST

    if request.method == 'GET':
        prefill = request.args.get('part_id', '')

        try:
            conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
            cur  = conn.cursor()

            # Use your real table names:
            cur.execute("SELECT operator_id, operator_name FROM operators ORDER BY operator_id")
            operator_options = cur.fetchall()

            cur.execute("SELECT machine_id, machine_name FROM machines ORDER BY machine_id")
            machine_options = cur.fetchall()

            cur.execute("SELECT material_id, material_name FROM materials ORDER BY material_id")
            material_options = cur.fetchall()
        except Exception as e:
            return f"Error loading options: {e}", 500
        finally:
            try: cur.close(); conn.close()
            except Exception: pass

        # If any list is empty, send user to create those first (optional)
        if not operator_options: return redirect(url_for('operator', stage=stage))
        if not machine_options:  return redirect(url_for('machine', stage=stage))
        if not material_options: return redirect(url_for('add_material', stage=stage))

        return render_template(
            'add_deposits.html',
            stage=stage,
            prefill_part_id=prefill,
            operator_options=operator_options,
            machine_options=machine_options,
            material_options=material_options
        )

    # POST: save the deposit
    try:
        part_id     = int(request.form['part_id'])
        file_name   = (request.form.get('file_name') or '').strip() or None
        operator_id = int(request.form['operator_id'])
        machine_id  = int(request.form['machine_id'])
        material_id = int(request.form['material_id'])
        notes       = request.form.get('notes')

        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO deposits (part_id, file_name, operator_id, machine_id, material_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (part_id) DO UPDATE SET
                file_name   = EXCLUDED.file_name,
                operator_id = EXCLUDED.operator_id,
                machine_id  = EXCLUDED.machine_id,
                material_id = EXCLUDED.material_id,
                notes       = EXCLUDED.notes
        """, (part_id, file_name, operator_id, machine_id, material_id, notes))
        conn.commit()
    except Exception as e:
        return f"Error inserting into deposits: {e}", 500
    finally:
        try: cur.close(); conn.close()
        except Exception: pass

    # continue to next page
    if (request.form.get('stage') == 'design_stage'):
        return redirect(url_for('design_stage', stage='design_stage', part_id=part_id))
    elif (request.form.get('stage') == 'post_process'):
        return redirect(url_for('post_process', stage='post_process', part_id=part_id))
    else:
        return redirect(url_for('index', stage=request.form.get('stage'), part_id=part_id))

@app.route('/overview', methods = ['GET', 'POST'])
def overview():
    try:
        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM (
                SELECT * FROM overview ORDER BY deposit_id DESC LIMIT 5
            ) AS latest
            ORDER BY deposit_id ASC
        """)
        rows = cur.fetchall()
        column_names = [desc[0] for desc in cur.description]
    except Exception as e:
        return f"Error fetching data from overview table: {e}"
    finally:
        cur.close()
        conn.close()

    return render_template("overview.html", rows=rows, columns=column_names)

@app.route('/enter_details', methods=['GET', 'POST'])
def enter_details():
    # GET: show the Part ID modal
    if request.method == 'GET':
        stage = request.args.get('stage') or session.get('stage') or 'design_stage'
        session['stage'] = stage
        return render_template('enter_details.html', stage=stage)

    # POST: user submitted a Part ID
    stage = request.form.get('stage') or session.get('stage')
    part_id_raw = request.form.get('part_id')

    if not stage or not part_id_raw:
        flash("Missing stage or Part ID.", "danger")
        return redirect(url_for('enter_details', stage=stage))

    try:
        part_id = int(part_id_raw)
    except ValueError:
        flash("Part ID must be a number.")
        return redirect(url_for('enter_details', stage=stage))

    # Check existence in deposits
    try:
        conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM deposits WHERE part_id = %s", (part_id,))
        exists = cur.fetchone() is not None
    except Exception as e:
        return f"Error checking deposits: {e}", 500
    finally:
        try:
            cur.close(); conn.close()
        except Exception:

            pass

    if not exists:
        # send to the add-deposit form (must allow GET)
        return redirect(url_for('add_deposits', stage=stage, part_id=part_id))

    # store and route to the designated page
    session['part_id'] = part_id
    session['stage'] = stage

    if stage == 'design_stage':
        return redirect(url_for('design_stage', stage=stage, part_id=part_id))
    elif stage == 'post_process':
        return redirect(url_for('post_process', stage=stage, part_id=part_id))
    elif stage in ('ircamera', 'tdimage', 'tdvideo'):
        return redirect(url_for('index', stage=stage, part_id=part_id))
    elif stage == 'in_process':
        # if they chose "In Process" first, send them to pick a sensor
        return redirect(url_for('select_sensor'))
    else:
        # fallback
        return redirect(url_for('index', stage=stage, part_id=part_id))

@app.route('/index')
def index():
    part_id= request.args.get('part_id') or session.get('part_id')
    stage = request.args.get('stage') or session.get('stage')
    message = request.args.get('message') 

    #if any are missing, return error

    grouped_files = {}

    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        files.sort()
        for file in files:
            rel_dir = os.path.relpath(root, app.config['UPLOAD_FOLDER'])
            rel_file = os.path.join(rel_dir, file) if rel_dir != '.' else file

            if rel_dir == '.':
                grouped_files.setdefault('', []).append(rel_file)
            else:
                folder = rel_dir.split(os.sep)[0]
                grouped_files.setdefault(folder, []).append(rel_file)

    return render_template('index.html', part_id=part_id,files=grouped_files,stage=stage,message=message)  # pass message to template

@app.route('/upload', methods=['POST'])
def upload_file():
    for file in request.files.getlist('files[]'):
        relative_path = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)
    return ('Files not selected')


@app.route('/design_stage', methods=['GET', 'POST'])
def design_stage():
    stage = request.args.get('stage') or request.form.get('stage') or 'design_stage'

    # ---- GET: show the form ----
    if request.method == 'GET':
        part_id = request.args.get('part_id') or ''
        return render_template('design_stage.html', stage=stage, part_id=part_id, message=request.args.get('message'))

    # ---- POST: save row ----
    part_id = request.form.get('part_id')
    file_name   = request.form.get('file_name')
    width   = request.form.get('width')
    height  = request.form.get('height')
    length  = request.form.get('length')
    notes2      = request.form.get('notes2')

    # Basic validation
    if not part_id or not file_name:
        return "Missing required fields!", 400

    # Validate required fields
    if not all([part_id,stage, file_name, notes2, width, height, length]):
        return "Missing required fields!"

    # Convert to correct types
    part_id = int(part_id)
    width = float(width) if width else None
    height = float(height) if height else None
    length = float(length) if length else None

    try:
        # Use context managers so connections/cursors close cleanly
        with psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id) as conn:
            with conn.cursor() as cur:
                # 1) Part must exist in deposits
                cur.execute("SELECT 1 FROM deposits WHERE part_id = %s", (part_id,))
                if cur.fetchone() is None:
                    # If your add form route is /deposits, change 'add_deposits' to 'deposits'
                    return redirect(url_for('add_deposits', stage=stage, part_id=part_id))

                # 2) Prevent duplicates in design_stage
                cur.execute("SELECT 1 FROM design_stage WHERE part_id = %s", (part_id,))
                if cur.fetchone():
                    return render_template('design_stage.html', stage=stage, part_id=part_id,
                                           message="⚠️ Part ID already exists in design_stage.")

                cur.execute("SELECT 1 FROM design_stage WHERE file_name = %s", (file_name,))
                if cur.fetchone():
                    return render_template('design_stage.html', stage=stage, part_id=part_id,
                                           message="⚠️ File name already exists in design_stage.")

                # 3) Insert (exactly 6 columns → 6 placeholders)
                cur.execute("""
                    INSERT INTO design_stage (part_id, file_name, length_mm, width_mm, height_mm, notes2)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (part_id, file_name, length, width, height, notes2))
                conn.commit()
    except Exception as e:
        return f"Error inserting values: {e}", 500

    return redirect(url_for('design_stage',
                            part_id=part_id,
                            stage=stage,
                            message='✅ Inserted values successfully'))


    # GET render
    return render_template("design_stage.html", part_id=part_id, stage=stage, message=request.args.get("message"))
    

@app.route('/preview_sensor1/<path:filename>')
def preview_sensor1(filename):
    return "Still in Process "

@app.route('/preview_sensor2/<path:filename>')
def preview_sensor2(filename):
    return "Still in Process "

def extract_ircamera_dataframe(filepath, expected_cols=20):
    with open(filepath, 'r') as file:
        lines = file.read().replace('\r', '').strip().split('\n')

    image_lines = []
    start_data = False

    for line in lines:
        line = line.strip()
        if not start_data:
            if "Image Data" in line:
                start_data = True
            continue
        if not line:
            continue


        parts = [p.strip() for p in line.split(';')]

        try:
            float_parts = [float(p) for p in parts if p != '']
            while len(float_parts) < expected_cols:
                float_parts.append(np.nan)
            image_lines.append(float_parts[:expected_cols])
        except ValueError:
            continue

    if not image_lines:
        raise ValueError("No valid numeric data found.")

    df = pd.DataFrame(image_lines)
    df.columns = [f"Col{i+1}" for i in range(expected_cols)]
    return df

@app.route('/preview_ircamera/<path:filename>')
def preview_ircamera(filename):
    part_id = session.get('part_id')
    stage = session.get('stage')


    safe_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if not safe_path.startswith(app.config['UPLOAD_FOLDER']):
        return "Invalid file path!", 400

    try:
        df = extract_ircamera_dataframe(safe_path)
        df_html = df.to_html(classes='table table-bordered', index=False, escape=False)
        return render_template('preview_ircamera.html', tables=[df_html], part_id=part_id,filename=filename,show_button=True, stage='ircamera')

    except Exception as e:
        return f"Error: {e}", 500

@app.route('/view_ircamera/<path:filename>')
def view_ircamera(filename):
    # Get extra params from request.args (query string)
    stage = request.args.get('stage')


    safe_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if not safe_path.startswith(app.config['UPLOAD_FOLDER']):
        return "Invalid file path!", 400

    try:
        df = extract_ircamera_dataframe(safe_path)  # You need to call your ircamera function here too!
        vmin, vmax = df.values.min(), df.values.max()

        def get_gradient_color(value):
            norm_val = (value - vmin) / (vmax - vmin)
            norm_val = max(0.0, min(1.0, norm_val))
            return plt.cm.plasma(norm_val)

        df_html = '<table class="table table-bordered" style="border-collapse: collapse;">'
        for row in df.values:
            df_html += '<tr>'
            for val in row:
                rgba = get_gradient_color(val)
                hex_color = matplotlib.colors.to_hex(rgba)
                df_html += f'<td style="background-color: {hex_color}; text-align: center;">{val:.2f}</td>'
            df_html += '</tr>'
        df_html += '</table>'


        return render_template('preview_ircamera.html', tables=[df_html], filename=filename, show_button=False, stage=stage)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/s3ircamera_update/<path:filename>', methods=['POST'])
def s3ircamera_update(filename):
    part_id = session.get('part_id')
    stage   = session.get('stage')

    if not part_id:
        return redirect(url_for('enter_details', stage='ircamera'))

    # Build absolute path and validate
    filepath = os.path.normpath(os.path.join(UPLOAD_FOLDER, filename))
    if not filepath.startswith(UPLOAD_FOLDER) or not os.path.isfile(filepath):
        return "Invalid or missing file.", 400

    # FRAME = string label from filename (basename, no extension)
    frame = os.path.splitext(os.path.basename(filename))[0]

    folder_name = os.path.basename(os.path.dirname(filename)) or "root"
    file_name   = f"{folder_name}_{datetime.now().strftime('%Y%m%d')}"  # <— use this in DB

    try:
        df = extract_ircamera_dataframe(filepath)

        with psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id) as conn:
            with conn.cursor() as cur:
                # check in_process for (part_id, file_name) — NOT the raw filename path
                cur.execute("SELECT COUNT(*) FROM in_process WHERE part_id=%s AND file_name=%s",
                            (part_id, file_name))
                if cur.fetchone()[0] > 0:
                    return redirect(url_for('index', part_id=part_id, stage=stage,
                                            message="⚠️ File already uploaded!"))

                # record dataset in in_process
                cur.execute("""
                    INSERT INTO in_process (part_id, file_name, sensor_id, type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (part_id, file_name) DO NOTHING
                """, (part_id, file_name, 3, 'IR_Camera'))

                # write heatmap rows to s3_ircamera with string frame
                for idx, row in df.iterrows():
                    row_index = idx + 1
                    cols = [float(row[i]) if pd.notna(row[i]) else None for i in df.columns]  # 20 numbers

                    cur.execute("""
                        INSERT INTO s3_ircamera (
                            part_id, sensor_id, file_name, frame, row_index,
                            Col_1, Col_2, Col_3, Col_4, Col_5, Col_6, Col_7, Col_8, Col_9, Col_10,
                            Col_11, Col_12, Col_13, Col_14, Col_15, Col_16, Col_17, Col_18, Col_19, Col_20
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (part_id, file_name, frame, row_index) DO NOTHING
                    """, (part_id, 3, file_name, frame, row_index, *cols))
                
                conn.commit()

        # optional: remove the source CSV once done
        try:
            os.remove(filepath)
        except OSError:
            pass

        return redirect(url_for('index', part_id=part_id, stage=stage,
                                message="File uploaded successfully"))
    except Exception as e:
        return f"Error uploading : {e}", 500


@app.route('/bulk_update/<path:folder>', methods=['POST'])
def bulk_update_folder(folder):
    part_id = session.get('part_id')
    stage   = session.get('stage')

    if not part_id:
        return redirect(url_for('enter_details', stage='ircamera'))

    base_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], folder))
    if not base_path.startswith(app.config['UPLOAD_FOLDER']) or not os.path.isdir(base_path):
        return "Invalid folder.", 400

    all_files = sorted([
        os.path.join(base_path, file)
        for file in os.listdir(base_path)
        if file.lower().endswith('.csv')
    ])

    success_count = 0
    fail_count    = 0

    for filepath in all_files:
        filename = os.path.relpath(filepath, app.config['UPLOAD_FOLDER'])
        try:
            df = extract_ircamera_dataframe(filepath)

            # Build dataset name and frame (match single-file route)
            folder_name = os.path.basename(os.path.dirname(filename))
            file_name   = f"{folder_name}_{datetime.now().strftime('%Y%m%d')}"  # DB file_name
            frame       = os.path.splitext(os.path.basename(filename))[0]       # label from CSV basename

            conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
            cur  = conn.cursor()

            # Ensure dataset in in_process
            cur.execute("""
                INSERT INTO in_process (part_id, file_name, sensor_id, type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (part_id, file_name) DO NOTHING
            """, (part_id, file_name, 3, 'IR_Camera'))

            # Insert rows; dedupe by (part_id, file_name, frame, row_index)
            for idx, row in df.iterrows():
                row_index = idx + 1
                cols = [float(row[i]) if pd.notna(row[i]) else None for i in df.columns]  # 20 numbers

                cur.execute("""
                    INSERT INTO s3_ircamera (
                        part_id, sensor_id, file_name, frame, row_index,
                        Col_1, Col_2, Col_3, Col_4, Col_5, Col_6, Col_7, Col_8, Col_9, Col_10,
                        Col_11, Col_12, Col_13, Col_14, Col_15, Col_16, Col_17, Col_18, Col_19, Col_20
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (part_id, file_name, frame, row_index) DO NOTHING
                """, (part_id, 3, file_name, frame, row_index, *cols))

            conn.commit()
            cur.close()
            conn.close()

            # Remove CSV after successful import
            try:
                os.remove(filepath)
            except OSError:
                pass

            success_count += 1

        except ValueError as ve:
            print(f"⚠️ Skipping {filename}: {ve}")
            fail_count += 1
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            fail_count += 1

    print(f"Bulk upload completed: {success_count} files uploaded, {fail_count} failed.")
    return ('', 204)


@app.route('/preview_tdvideo/')
def preview_tdvideo():
    return "Still in Process "

@app.route('/preview_tdimage')
def preview_tdimage():
    return "Still in Process "

@app.route('/post_process', methods=['POST','GET'])
def post_process():
    stage = request.args.get('stage')
    part_id = session.get('part_id')
    

    if request.method == 'POST':
        stage = request.form.get('stage')
        file_name = request.form.get('file_name')
        part_id = request.form.get('part_id')
        hardness = request.form.get('hardness')
        uts = request.form.get('uts')


        hardness = float(hardness) if hardness else None
        uts = float(uts) if uts else None
        

        try:
            conn = psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM post_process WHERE File_name = %s", (file_name,))
            file_exists = cur.fetchone()[0]

            if file_exists > 0:
                conn.commit()
                curr.close()
                conn.close()
                # File already uploaded — show preview with message
                return render_template('post_process.html',part_id=part_id,stage=stage,message="⚠️ File already uploaded!")
            

            cur.execute("""
                INSERT INTO post_process(part_id, file_name, hardness, uts)
                VALUES (%s, %s, %s, %s)
            """, (part_id,file_name,hardness, uts))
            conn.commit()

            return redirect(url_for('post_process',part_id=part_id,stage=stage,message = 'Inserted values sucessfully'))

        except Exception as e:
            return f"Error inserting values {e}"

        finally:
            cur.close()
            conn.close()  

            # Redirect to index with success message
    return render_template("post_process.html",part_id=part_id,stage=stage,message=request.args.get("message"))
        

@app.route('/generate_video/<path:folder>')
def generate_folder_video(folder):
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    video_name = f"{folder.replace('/', '_')}_thermal_video.mp4"
    output_path = os.path.join("static", "videos", video_name)

    #  If video already exists, just serve it
    if os.path.exists(output_path):
        return redirect(url_for('static', filename=f"videos/{video_name}"))

    os.makedirs("static/videos", exist_ok=True)

    try:
        # Collect all CSV files recursively in folder
        csv_files = sorted([
            os.path.join(root, file)
            for root, _, files in os.walk(base_path)
            for file in files if file.endswith('.csv')
        ])

        if not csv_files:
            return "No CSV files found in folder", 404

        writer = imageio.get_writer(output_path, fps=40)

        for file in csv_files:
            try:
                df = extract_image_dataframe(file)
                df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
                image = create_colored_image(df)
                writer.append_data(image)
            except Exception as e:
                print(f"Skipping {file}: {e}")
                continue

        writer.close()
        return redirect(url_for('static', filename=f"videos/{video_name}"))

    except Exception as e:
        print(f"Video generation failed: {e}")
        return f"Error: {e}", 500

#having some errors 
@app.route('/generate_video_top_level')
def generate_top_level_video():
    output_path = os.path.join("static", "videos", "top_level_video.mp4")

    # If video already exists, just serve it
    if os.path.exists(output_path):
        return redirect(url_for('static', filename=f"videos/{video_name}"))

    os.makedirs("static/videos", exist_ok=True)

    try:
        top_files = []
        base_path = app.config['UPLOAD_FOLDER']

        for file in os.listdir(base_path):
            if file.endswith('.csv'):
                top_files.append(os.path.join(base_path, file))

        top_files.sort()
        writer = imageio.get_writer(output_path, fps=10)

        for file in top_files:
            try:
                df = extract_image_dataframe(file)
                df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
                image = create_colored_image(df)
                writer.append_data(image)
            except Exception as e:
                print(f"Skipping {file}: {e}")
                continue

        writer.close()
        return redirect(url_for('static', filename=f"videos/{video_name}"))

    except Exception as e:
        print(f"Top-level video generation failed: {e}")
        return f"Error: {e}", 500


def create_colored_image(df):
    fig, ax = plt.subplots()
    ax.imshow(df.values, cmap='plasma')  # 'plasma' works well for thermal
    ax.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    image = Image.open(buf)
    return np.array(image)


@app.route('/clear_selected', methods=['POST'])
def clear_selected():
    stage = request.form.get('stage')

    selected_items = request.form.getlist('selected_files')

    for item in selected_items:
        full_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], item))

        if os.path.isdir(full_path):
            # Delete all files and subfolders in the folder
            for root, dirs, files in os.walk(full_path, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            try:
                os.rmdir(full_path)
            except FileNotFoundError:
                pass

            # Delete corresponding video file if it exists
            video_name = f"{item.strip('/').replace('/', '_')}_thermal_video.mp4"
            video_path = os.path.join("static", "videos", video_name)
            if os.path.exists(video_path):
                os.remove(video_path)

        elif os.path.isfile(full_path):
            os.remove(full_path)

        # Clean up empty parent directories
        folder = os.path.dirname(full_path)
        while folder and folder != app.config['UPLOAD_FOLDER']:
            if os.path.exists(folder) and not os.listdir(folder):
                os.rmdir(folder)
                folder = os.path.dirname(folder)
            else:
                break

    return redirect(url_for('index', stage=stage))


@app.route('/delete/<path:filename>', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)

        folder = os.path.dirname(file_path)
        while folder and folder != app.config['UPLOAD_FOLDER']:
            if not os.listdir(folder):
                os.rmdir(folder)
                folder = os.path.dirname(folder)
            else:
                break

    return redirect(url_for('index'))

def read_csv_page(path, start, limit, encoding="latin1"):
    with open(path, newline='', encoding=encoding) as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        rows = list(islice(reader, start, start + limit))
    return headers, rows

def count_csv_data_rows(path, encoding="latin1"):
    with open(path, newline='', encoding=encoding) as f:
        total = sum(1 for _ in f)
    return max(total - 1, 0)

@app.route('/preview_pico_log/<path:filename>')
def preview_pico_log(filename):
    part_id = request.args.get('part_id', type=int) or session.get('part_id')
    per_page = request.args.get('per_page', default=1000, type=int)
    page     = request.args.get('page', default=1, type=int)
    stage = request.args.get('stage')

    abs_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.isfile(abs_path):
        return f"File {filename} not found", 404

    total_rows  = count_csv_data_rows(abs_path)
    total_pages = max(ceil(total_rows / per_page), 1)
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * per_page

    headers, rows = read_csv_page(abs_path, start=start, limit=per_page)

    return render_template(
        'pico_log_preview.html',
        filename=filename,
        headers=headers,
        rows=rows,
        page=page,
        per_page=per_page,
        total_rows=total_rows,
        total_pages=total_pages,
        part_id=part_id, 
        stage=stage
    )


def extract_pico_log(file_name, max_rows=None):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    if not os.path.isfile(filepath):
        return f"file {file_name} not found", 404

    df = pd.read_csv(filepath, nrows=max_rows, encoding="latin1")
    rows = df.values.tolist()

    return rows 

@app.route('/pico_log', methods=['GET', 'POST'])
def pico_log():
    filename = request.form.get('filename') or request.args.get('filename')
    part_id = request.form.get('part_id') or session.get('part_id')
    stage   = request.form.get('stage')   or session.get('stage') or 'pico_log'

    if not part_id:
        flash("Pick a Part ID first.", "danger")
        return redirect(url_for('enter_details', stage='pico_log'))

    if not filename:
        return "Missing filename.", 400
        
    # Resolve and validate path under UPLOAD_FOLDER
    abs_path = os.path.normpath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if not abs_path.startswith(app.config['UPLOAD_FOLDER']) or not os.path.isfile(abs_path):
        return "File not found.", 404

    try:
        with psycopg2.connect(host=hostname, dbname=database, user=username, password=pwd, port=port_id) as conn:
            with conn.cursor() as cur:
                # Stream rows; assume columns: mode, time, area, power, duty
                batch = []
                with open(abs_path, newline='', encoding="latin1") as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)  # skip header
                    for row in reader:
                        if not row:
                            continue
                        mode  = row[0]
                        time  = row[1]
                        area  = row[2]
                        power = row[3]
                        duty  = row[4]

                        batch.append((int(part_id), filename, mode, time, area, power, duty))

                        if len(batch) >= 1000:
                            cur.executemany(
                                """INSERT INTO pico_log
                                   (part_id, file_name, mode, time, area, power, duty)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                                batch
                            )
                            batch.clear()

                if batch:
                    cur.executemany(
                        """INSERT INTO pico_log
                           (part_id, file_name, mode, time, area, power, duty)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        batch
                    )

                conn.commit()

        # (optional) remove the CSV after import
        try: 
            os.remove(abs_path)
        except OSError: 
            pass

        flash("Pico Log uploaded to database.", "success")
        return redirect(url_for('index', stage='pico_log', part_id=part_id))
    except Exception as e:
        return f"Error uploading : {e}", 500
    

if __name__ == '__main__':
    app.run(port=5001, debug=True)