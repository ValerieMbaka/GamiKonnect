import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os
import environ
import logging

logger = logging.getLogger(__name__)


def initialize_firebase():
    try:
        # Check if Firebase is already initialized to avoid duplicate initialization errors
        if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            return firebase_admin.get_app()
        
        # 🎮 AUTOMATIC ENVIRONMENT DETECTOR
        # Render automatically provides the 'RENDER' environment variable live
        if os.environ.get('RENDER'):
            # Production path on Render
            cred_path = os.path.join(settings.BASE_DIR, 'gamikonnect-34d65-firebase-adminsdk-fbsvc-d3e3498b9f.json')
            logger.info("Routing to Render Secret File")
        else:
            # Localhost development fallback path
            cred_path = os.path.join(settings.BASE_DIR, 'django-4c5e9-firebase-adminsdk.json')
            logger.info("Routing to local machine file.")
        
        # Verify that the designated configuration file actually exists
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found at: {cred_path}")
            return None
        
        # Authenticate and spin up the Firebase Admin app instance
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(cred)
        
        logger.info("Firebase Admin SDK initialized successfully")
        return app
    
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None


# Initialize Firebase when Django starts up
initialize_firebase()