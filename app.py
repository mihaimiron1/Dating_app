from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd
from backend.main import load_data, recommend_users_by_id, interact_with_recommended_users,  give_friends, calculate_similarity, get_vector3, add_user_in_data, find_interests

from sklearn.preprocessing import MultiLabelBinarizer

app = Flask(__name__)
# Cheia se setează prin variabila de mediu SECRET_KEY; fără ea se generează una temporară
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)


# Load the necessary data and similarity matrix globally


# Citirea fișierului JSON cu utilizatori
def load_users():
    try:
        with open('login_users.json', 'r') as file:
            return json.load(file)['users']
    except FileNotFoundError:
        return []


# Ruta pentru pagina principală
@app.route('/')
def index():
    return render_template('index.html')










@app.route('/profil', methods=['GET', 'POST'])
def profil():
    user_id = session.get('user_id')
    if not user_id:
        flash("Te rugăm să te conectezi mai întâi!", 'error')
        return redirect(url_for('login'))

    # Încarcă datele utilizatorilor
    users_json = load_users()
    user = next((u for u in users_json if u['ID'] == user_id), None)
    
    if not user:
        flash("Utilizatorul nu a fost găsit!", 'error')
        return redirect(url_for('index'))

    # Încarcă date suplimentare pentru utilizator
    data, _, _ = load_data()
    user_data = data[data['ID'] == user_id].iloc[0]
    


    
    # Preia informațiile de profil
    first_name = user["Prenume"]
    last_name = user["Nume"]
    age = int(user_data["Age"])
    location = user_data["Location"]
    photo_path = user_data["Photo_Path"]
    height = user_data["Height"]
    interests = find_interests(user_id)
    
    if request.method == 'POST':
        # Actualizează profilul
        updated_first_name = request.form['first_name']
        updated_last_name = request.form['last_name']
        updated_location = request.form['location']
        update_height = request.form['height']
        update_interests = request.form['interests']
        

        # Actualizează datele utilizatorului în fișierul JSON
        user['Prenume'] = updated_first_name
        user['Nume'] = updated_last_name
        user_data['Location'] = updated_location
        user_data['Height'] = update_height
        user_data['Interests'] = update_interests
        
        # Salvează modificările
        with open('login_users.json', 'w') as file:
            json.dump({'users': users_json}, file, indent=4)
        
        flash("Profilul a fost actualizat cu succes!", 'success')
        return redirect(url_for('profil'))
    interests = interests.split()
    return render_template('profil.html', first_name=first_name, last_name=last_name, age=age, location=location, photo_path=photo_path, height=height, interests=interests)




@app.route('/friends')
def friends():
    friends_list = []

    user_id = session.get('user_id')
    if not user_id:
        flash("Te rugăm să te conectezi mai întâi!", 'error')
        return redirect(url_for('login'))
    users_json = load_users()
    data, interactions_matrix, _ = load_data()
    user_friends= give_friends(user_id, interactions_matrix)
 
    
    for friend_id in user_friends:
        user_info = next((user for user in users_json if user["ID"] == friend_id), None)
        if not user_info:
            continue
        friend_data = data[data['ID'] == friend_id]
        if friend_data.empty:
            continue

        friend_row = friend_data.iloc[0]
        friends_list.append({
            "first_name": user_info["Prenume"],
            "last_name": user_info["Nume"],
            "age": int(friend_row["Age"]),
            "location": friend_row["Location"],
            "photo_path": friend_row["Photo_Path"]
        })


    #print("Filtered data IDs (types):", filtered_data['ID'].apply(type).unique())
    return render_template('friends.html', friends=friends_list)


# Ruta pentru pagina de înregistrare
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = load_users()
        for user in users:
            if user['Email'] == email:
                flash("Acest email este deja înregistrat!", 'error')
                return redirect(url_for('register'))
        session['new_user_email'] = email
        session['new_user_password_hash'] = generate_password_hash(password)
        

        return redirect(url_for('create_profile', user_id=len(users) + 1))

    return render_template('register.html')


def save_users(data):
    with open('login_users.json', 'w') as file:
        json.dump(data, file, indent=4)



@app.route('/create_profile/<int:user_id>', methods=['GET', 'POST'])
def create_profile(user_id):
    if request.method == 'POST':
        try:
            # Adună datele din formular
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            age = request.form['age']
            height = request.form['height']
            hair_color = request.form['hair_color']
            interests = request.form['interests']  # Split după virgulă
            user_gender = request.form['user_gender']
            preferred_gender = request.form['preferred_gender']
            age_min = request.form['min_age']
            age_max = request.form['max_age']
            location = request.form['location']

            print(f'Form Data Received: {first_name}, {last_name}, {age}, {height}, {hair_color}, {interests}, {user_gender}, {preferred_gender}, {age_min}, {age_max}, {location}')
            
            # Calculează vectorii de locație
            vectorX, vectorY, vectorZ = get_vector3(location)

            # Convertește datele de gen
            user_gender = 1 if user_gender == 'male' else 0
            preferred_gender = 1 if preferred_gender == 'male' else 0

            # Manevrarea pozei
            photo = request.files['photo']
            photo_path = f'static/images/{photo.filename}'
            photo.save(photo_path)

            # Procesare utilizatori
            users = load_users()
            id_user_new = len(users) + 1
            age = int(age)
            height = int(height)
            age_min = int(age_min)
            age_max = int(age_max)

            new_user = {
                "ID": id_user_new,
                "Age": age,
                "Height": height,
                "Hair_Color": hair_color,
                "interest": interests,  # Interesele ca un singur string
                "Preferred_Gender": preferred_gender,
                "Gender": user_gender,
                "Location": location,
                "Photo_Path": photo_path,
                "Age_Min": age_min,
                "Age_Max": age_max,
                "Vector_X": vectorX,
                "Vector_Y": vectorY,
                "Vector_Z": vectorZ
            }

            # Încearcă să adaugi utilizatorul
            add_user_in_data(new_user)
            
            # Procesare date de login
            email = session.get('new_user_email')
            password_hash = session.get('new_user_password_hash')
            new_user = {
                'Email': email,
                'Parola_Hash': password_hash,
                'Nume': last_name,
                'Prenume': first_name,
                'ID': id_user_new
            }

            users.append(new_user)
            with open('login_users.json', 'w') as file:
                json.dump({'users': users}, file, indent=4)

            print(f"User {id_user_new} successfully added!")
            return '', 204

        except Exception as e:
            print(f"Error saving profile for user {user_id}: {e}")
            # Dacă apare o eroare, returnează codul 500 (Internal Server Error)
            return 'Internal Server Error', 500

    # GET request - afișează formularul
    return render_template('create_profile.html', user_id=user_id)






# Ruta pentru pagina de conectare
@app.route('/conect', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = load_users()
        user_found = None
        for user in users:
            if user['Email'] == email and check_password_hash(user['Parola_Hash'], password):
                user_found = user
                break
        if user_found:
            session['user_id'] = user_found['ID']
            
            return redirect(url_for('dating_page'))  # Redirect to dating page
        else:
            flash("Email sau parolă incorectă!", 'error')
    return render_template('conect.html')  # Sau logica pentru conectare


@app.route('/dating_page', methods=['GET', 'POST'])
def dating_page():
    user_id = session.get('user_id')
    if not user_id:
        flash("Te rugăm să te conectezi mai întâi!", 'error')
        return redirect(url_for('login'))
    

    print(f"Current User ID: {user_id}")
    data, interactions_matrix, interests_df = load_data()
    similarity_matrix = calculate_similarity(data, interests_df)
    recommended_user = recommend_users_by_id(user_id, data, similarity_matrix, interactions_matrix)
    

    if not recommended_user:
        return jsonify({"error": "No recommended users found."}), 404

    users = load_users()
    user = next((u for u in users if u['ID'] == recommended_user[0]['ID']), None)

    if user:
        session['user_recom_id'] = recommended_user[0]['ID']
        first_name = user['Prenume']
        last_name = user['Nume']
        location = recommended_user[0]['Location']
        age = recommended_user[0]['Age']
        photo = recommended_user[0]['Photo_Path']
    else:
        first_name = "Necunoscut"
        last_name = "Necunoscut"
        location = ""
        age = 0
        photo = ""

    return render_template('dating_page.html', recommended_user={
        'photo_path': photo,
        'first_name': first_name,
        'last_name': last_name,
        'age': age,
        'location': location
    })


@app.route('/get_next_user', methods=['GET'])
def get_next_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error ": "User not logged in"}), 401

    print(f"Current User ID: {user_id}")
    data, interactions_matrix, interests_df = load_data()
    similarity_matrix = calculate_similarity(data, interests_df)
    recommended_user = recommend_users_by_id(user_id, data, similarity_matrix, interactions_matrix)
    print(f"Recommended Users: {recommended_user[0]['ID']}")
    print(f"Recommended Users: {recommended_user[0]['Photo_Path']}")  

    if not recommended_user:
        return jsonify({"error": "No recommended users found."}), 404

    users = load_users()
    user = next((u for u in users if u['ID'] == recommended_user[0]['ID']), None)

    if user:
        session['user_recom_id'] = recommended_user[0]['ID']
        return jsonify({
            'photo_path': recommended_user[0]['Photo_Path'],
            'first_name': user['Prenume'],
            'last_name': user['Nume'],
            'age': recommended_user[0]['Age'],
            'location': recommended_user[0]['Location']
        })
    else:
        return jsonify({"error": "User details not found."}), 404

    


@app.route('/like_this_user', methods=['GET'])
def like_this_user():
    user_id = session.get('user_id')
    user_recod_id=session.get('user_recom_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401
    if not user_recod_id:
        return jsonify({"error": "Recommended user not found"}), 402


    # Obținem recomandările pe baza ID-ului utilizatorului
    _, interactions_matrix, _ = load_data()
    interact_with_recommended_users(user_id, user_recod_id, interactions_matrix, 1)

    return redirect(url_for('get_next_user'))




@app.route('/dislike_this_user', methods=['GET'])
def dislike_this_user():
    user_id = session.get('user_id')
    user_recod_id=session.get('user_recom_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401
    if not user_recod_id:
        return jsonify({"error": "Recommended user not found"}), 402


    # Obținem recomandările pe baza ID-ului utilizatorului
    _, interactions_matrix, _ = load_data()
    interact_with_recommended_users(user_id, user_recod_id, interactions_matrix, 0.5)
    
    return redirect(url_for('get_next_user'))



if __name__ == '__main__':
    app.run(debug=True)
