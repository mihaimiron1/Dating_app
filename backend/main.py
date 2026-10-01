from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MultiLabelBinarizer
from opencage.geocoder import OpenCageGeocode

def get_coordinates(location):
    api_key = os.environ.get('OPENCAGE_API_KEY')
    if not api_key:
        raise RuntimeError("Setează variabila de mediu OPENCAGE_API_KEY pentru geocodare.")
    geocoder = OpenCageGeocode(api_key)
    try:
        result = geocoder.geocode(location)
        if result and len(result):
            return result[0]['geometry']['lat'], result[0]['geometry']['lng']
        else:
            return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None
    
def get_vector3(location):
    lat, long = get_coordinates(location)
    lat_rad = np.radians(lat)
    long_rad = np.radians(long)

    # Transformare în vectori 3D
    x = np.cos(lat_rad) * np.cos(long_rad)
    y = np.cos(lat_rad) * np.sin(long_rad)
    z = np.sin(lat_rad)
    return x, y, z



# Încărcăm matricea interacțiunilor și datele procesate
def load_data():
    interactions_matrix = pd.read_csv('APA_PR/interact.csv', index_col=0)
    data = pd.read_csv('APA_PR/procesed_data.csv')
    data_orig = pd.read_csv('APA_PR/dating_data.csv')
    mlb = MultiLabelBinarizer()
    interests_matrix = mlb.fit_transform(data_orig['Interests'].str.split())  # Split pe spațiu pentru a crea lista de interese
    interests_df = pd.DataFrame(interests_matrix, columns=mlb.classes_)
    return data, interactions_matrix, interests_df


def identify_interest_columns(dataframe):
            # Selectăm coloanele cu valori binare (0 și 1) care nu sunt categorice evidente
    interest_columns = [
        column for column in dataframe.columns
        if dataframe[column].dropna().isin([0, 1]).all()  # Verifică dacă toate valorile sunt 0 sau 1
        and column not in ["ID", "Gender", "Preferred_Gender"]
    ]
    return interest_columns

def extract_interests(row, interests_columns):
    interests = [interest for interest in interests_columns if row[interest] == 1]
    return ", ".join(interests)  # Interesele vor fi returnate sub formă de string, separate prin virgulă

def find_interests(user_id):
    df = pd.read_csv('APA_PR/procesed_data.csv')

    interests_columns = identify_interest_columns(df)
    df["Interests"] = df.apply(lambda row: extract_interests(row, interests_columns), axis=1)
    return df[df["ID"] == user_id]["Interests"].values[0]




def add_user_in_data(new_user):
    data,interactions_matrix,_ = load_data()
    all_interests = list(data.columns[10:-3])

    user_interest_list = [interest.strip() for interest in new_user["interest"].split(",")]

    # Verificăm și actualizăm lista globală a intereselor
    new_interests = set(user_interest_list) - set(all_interests)
    print(f"Interese noi: {new_interests}")
    for interest in new_interests:
        data.insert(len(data.columns) - 4, interest, 0)

    all_interests = list(data.columns[10:-3])

    # Funcția care transformă interesele în format binar
    def binarize_interests(user_interest, all_interests):
        return [1 if interest in user_interest else 0 for interest in all_interests]

    # Construim un rând pentru noul utilizator
    new_user_row = [
        new_user["ID"],
        new_user["Gender"],
        new_user["Age"],
        new_user["Height"],
        new_user["Hair_Color"],
        new_user["Preferred_Gender"],
        new_user["Location"],
        new_user["Photo_Path"],
        new_user["Age_Min"],
        new_user["Age_Max"]
    ] + binarize_interests(user_interest_list, all_interests) + [
        new_user["Vector_X"],
        new_user["Vector_Y"],
        new_user["Vector_Z"]   
    ]
    # Actualizăm lista de coloane pentru a include noile coloane de interese
    columns = [col for col in data.columns.tolist() if col not in ["Vector_X", "Vector_Y", "Vector_Z"]]
    columns = columns + ["Vector_X", "Vector_Y", "Vector_Z"]

    # Adăugăm noul utilizator în DataFrame
    new_user_df = pd.DataFrame([new_user_row], columns=columns)
    data = pd.concat([data, new_user_df], ignore_index=True)
    data.to_csv('APA_PR/procesed_data.csv', index=False)
    # Adaugă un nou rând la final
    new_row = [0] * len(interactions_matrix.columns)  # Toate valorile sunt 0
    interactions_matrix.loc[len(interactions_matrix) + 1] = new_row

    # Adaugă o nouă coloană la final
    new_column = [0] * len(interactions_matrix)  # Toate valorile sunt 0
    interactions_matrix[len(interactions_matrix.columns) + 1] = new_column

    # Salvează rezultatul înapoi într-un fișier CSV (opțional)
    interactions_matrix.to_csv('APA_PR/interact.csv')









def update_interaction_matrix(new_interaction):
    new_interaction.to_csv('APA_PR/interact.csv', index=False)


# Funcția de recomandare a utilizatorilor
def recommend_users_by_id(user_id, data, similarity_matrix, interactions_matrix, top_n=2):
    if user_id not in interactions_matrix.index:
        return "ID-ul utilizatorului nu există în matricea de interacțiuni."

    user_index = data[data['ID'] == user_id].index[0]
    similarity_scores = similarity_matrix[user_index]

    preferred_gender = data.loc[user_index, 'Preferred_Gender']
    age_min = data.loc[user_index, 'Age_Min']
    age_max = data.loc[user_index, 'Age_Max']

    # Filtrare pe baza preferințelor de gen și vârstă
    filtered_data = data[(data['Gender'] == preferred_gender) & 
                         (data['Age'] >= age_min) & 
                         (data['Age'] <= age_max)]

    if filtered_data.empty:
        return "Nu există utilizatori care să se potrivească pe baza preferințelor."
    
    # Excludem utilizatorii deja interacționați
    interacted_users = interactions_matrix.iloc[user_index]
    
    interacted_users = interacted_users[interacted_users > 0].index.tolist()
    #print("uSeR_Iassadada::::::::::::::::",interacted_users)
    interacted_users = [int(user_id) for user_id in interacted_users]

    filtered_data = filtered_data[~filtered_data['ID'].isin(interacted_users)]

    #print("filtered_data_secod::::::::::::::::",filtered_data['ID'])

    if filtered_data.empty:
        print("Nu există utilizatori noi de recomandat.")
        return "Nu există utilizatori noi de recomandat."
        
    

    #persoane asemanataore cu useul logat
    find_like_pers=data[
        (data['Gender'] == data.loc[user_index, 'Gender']) &  
        (data['Preferred_Gender'] == data.loc[user_index, 'Preferred_Gender'])
    
    ]
    if find_like_pers.empty:
        pass
    else:
        
        #cel mai asemanator user cu cel curent
        like_pers_user = similarity_scores[filtered_data.index].argsort()[::-1][:1]
        
        #transformam in int
        like_pers_user=int(like_pers_user[0])


        #extragem persoanele la care userul a dat like
        like_pers_interact=interactions_matrix.iloc[like_pers_user-1]
        like_pers_interact = like_pers_interact[like_pers_interact > 0].index.tolist()

        like_interact=[]
        for s in like_pers_interact:
            like_interact.append(int(s))
        like_interact = [i - 1 for i in like_interact]
        #marim scorul pers la care userul asemanator a dat like
        similarity_scores[like_interact] += 0.07


    # Calculăm cei mai similari utilizatori
    similar_users = similarity_scores[filtered_data.index].argsort()[::-1][:top_n]
    recommended_user_ids = filtered_data.iloc[similar_users]

    # Return a list of user dictionaries with necessary information
    return recommended_user_ids.to_dict(orient='records')

# Funcția pentru interacțiuni cu utilizatorii recomandați
def interact_with_recommended_users(user_id, recommended_user, interactions_matrix, interaction):
    interactions_matrix.iloc[user_id-1, recommended_user-1] = interaction
    interactions_matrix.to_csv('APA_PR/interact.csv')
 
# Funcția pentru a vedea prietenii
def give_friends(user_id, interactions_matrix):
    a = interactions_matrix.iloc[:, user_id - 1].tolist()  # Extrage coloana
    choise_1 = [i for i, val in enumerate(a) if val == 1]
    interact = [int(s) for s in choise_1]
    friend_user = []

    for s in interact:
        if interactions_matrix.iloc[user_id - 1, s] == 1:
            print(f"Utilizatorul {s+1} este prieten cu utilizatorul {user_id}.")
            friend_user.append(s+1)
            
    
    return friend_user

def calculate_similarity(data, interests_df):
    feature_columns = ['Vector_X', 'Vector_Y', 'Vector_Z'] + list(interests_df.columns)
    feature_matrix = data[feature_columns]
    scaler = StandardScaler()
    feature_matrix_scaled = scaler.fit_transform(feature_matrix)
    similarity_matrix = cosine_similarity(feature_matrix_scaled)
    return similarity_matrix


