import firebase_admin
from firebase_admin import credentials
from django.conf import settings
import os
import environ
import logging

logger = logging.getLogger(__name__)


def initialize_firebase():
    try:
        # Check if already initialized
        if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
            return firebase_admin.get_app()
        
        # Use the service account key file you uploaded
        cred_path = os.path.join(settings.BASE_DIR, 'google-services.json')
        
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found at: {cred_path}")
            return None
        
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(cred)
        
        logger.info("Firebase Admin SDK initialized successfully")
        return app
    
    except Exception as e:
        logger.error(f"Error initializing Firebase: {e}")
        return None


# Initialize Firebase when Django starts
initialize_firebase()
