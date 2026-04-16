import { initializeApp, getApp } from "https://www.gstatic.com/firebasejs/12.6.0/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updateProfile,
    sendEmailVerification,
    sendPasswordResetEmail,
} from "https://www.gstatic.com/firebasejs/12.6.0/firebase-auth.js";

class FirebaseManager {
    constructor() {
        this.app = null;
        this.auth = null;
        this.init();
    }

    init() {
        const configElement = document.getElementById('firebase-config-data');
        if (!configElement) {
            console.warn('Firebase configuration data not found.');
            return;
        }

        try {
            const firebaseConfig = JSON.parse(configElement.textContent);
            this.app = initializeApp(firebaseConfig);
            this.auth = getAuth(this.app);
            this.exposeGlobals();
        } catch (error) {
            console.error('Firebase initialization error:', error);
        }
    }

    exposeGlobals() {
        window.firebaseAuthCreateUser = async (email, password) => {
            try {
                return await createUserWithEmailAndPassword(this.auth, email, password);
            } catch (error) {
                console.error('Error creating user:', error);
                throw error;
            }
        };

        window.firebaseAuthSignIn = async (email, password) => {
            try {
                return await signInWithEmailAndPassword(this.auth, email, password);
            } catch (error) {
                console.error('Error signing in:', error);
                throw error;
            }
        };

        window.firebaseSendEmailVerification = async (user) => {
            try {
                await sendEmailVerification(user);
                return true;
            } catch (error) {
                console.error('Error sending verification email:', error);
                throw error;
            }
        };
        
        window.firebaseAuthInstance = this.auth;
    }
}

document.addEventListener('DOMContentLoaded', () => new FirebaseManager());

export {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updateProfile,
    sendEmailVerification,
    sendPasswordResetEmail,
};