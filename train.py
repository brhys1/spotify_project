import pandas as pd
from sklearn.model_selection import train_test_split # splits training from real data 
from sklearn.pipeline import Pipeline
# applies transformations to diff sub # chains processing sets
from sklearn.compose import ColumnTransformer
from category_encoders import TargetEncoder
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from  sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor  # You can swap with any regressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score

cols_to_use = ['lyrics', 'track_popularity', 'track_artist', 'track_album_release_date',
               'danceability', 'energy', 'speechiness', 'acousticness',
               'instrumentalness', 'liveness', 'valence', 'tempo', 'duration_ms']

data = pd.read_csv('dataset.csv', usecols=cols_to_use, low_memory=False)
data = data.dropna(subset=['track_popularity'])

data['lyrics'] = data['lyrics'].fillna('')
# we will use these variables will predict track_popularity
numerical_features = ['danceability', 'energy', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'duration_ms']
text_feature = 'lyrics'
target = 'track_popularity'
encode_artist = 'track_artist'

text_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=1000)),
    ('to_dense', FunctionTransformer(lambda x: x.toarray(), accept_sparse=True))
])

preprocessor = ColumnTransformer(
    transformers=[
        ('numerical', StandardScaler(), numerical_features),
        ('text', text_pipeline, text_feature),
        ('artist', TargetEncoder(), [encode_artist])
    ],
    sparse_threshold=0
)

X = data[numerical_features + [text_feature, encode_artist]]
y = data[target]

pipeline = Pipeline(
    steps=[
        ('preprocessor', preprocessor),
        #('regressor', RandomForestRegressor(n_estimators=1000, random_state=42))    
        ('regressor', HistGradientBoostingRegressor(random_state=42))
    ]
)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)

mse = mean_squared_error(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MSE: {mse:.2f}")
print(f"MAE: {mae:.2f}")
print(f"R² Score: {r2:.2f}")

