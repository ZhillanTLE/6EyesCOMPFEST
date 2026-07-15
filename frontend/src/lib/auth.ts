/**
 * auth.ts — Firebase client-side authentication helpers.
 *
 * Provides:
 *  - initFirebase()        : initializes Firebase App once
 *  - signInWithGoogle()    : Google Sign-In popup
 *  - signInWithEmail()     : email + password sign-in
 *  - signOut()             : sign out
 *  - getIdToken()          : returns fresh Firebase JWT for API calls
 *  - onAuthStateChanged()  : subscribe to auth state changes
 *
 * Set the following env vars in frontend/.env.local:
 *   NEXT_PUBLIC_FIREBASE_API_KEY
 *   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
 *   NEXT_PUBLIC_FIREBASE_PROJECT_ID
 */

import { initializeApp, getApps, FirebaseApp } from "firebase/app";
import {
  getAuth,
  Auth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged as firebaseOnAuthStateChanged,
  User,
} from "firebase/auth";

// ---------------------------------------------------------------------------
// Firebase App init (singleton)
// ---------------------------------------------------------------------------
let app: FirebaseApp | null = null;
let auth: Auth | null = null;

function initFirebase(): Auth {
  if (auth) return auth;

  const firebaseConfig = {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  };

  if (!firebaseConfig.apiKey) {
    console.warn(
      "[Auth] Firebase env vars not set. Authentication will be skipped (dev mode)."
    );
    // Return a stub auth that always resolves as unauthenticated
    return null as unknown as Auth;
  }

  if (!getApps().length) {
    app = initializeApp(firebaseConfig);
  } else {
    app = getApps()[0];
  }

  auth = getAuth(app);
  return auth;
}

// ---------------------------------------------------------------------------
// Public helpers
// ---------------------------------------------------------------------------

/** Sign in with Google via popup. Returns the signed-in User. */
export async function signInWithGoogle(): Promise<User> {
  const firebaseAuth = initFirebase();
  if (!firebaseAuth) throw new Error("Firebase not configured.");
  const provider = new GoogleAuthProvider();
  const result = await signInWithPopup(firebaseAuth, provider);
  return result.user;
}

/** Sign in with email + password. Returns the signed-in User. */
export async function signInWithEmail(email: string, password: string): Promise<User> {
  const firebaseAuth = initFirebase();
  if (!firebaseAuth) throw new Error("Firebase not configured.");
  const result = await signInWithEmailAndPassword(firebaseAuth, email, password);
  return result.user;
}

/** Sign out the current user. */
export async function signOut(): Promise<void> {
  const firebaseAuth = initFirebase();
  if (!firebaseAuth) return;
  await firebaseSignOut(firebaseAuth);
}

/**
 * Get a fresh Firebase ID token for the currently signed-in user.
 * Returns null if no user is signed in.
 * Pass this in the `Authorization: Bearer <token>` header of API calls.
 */
export async function getIdToken(): Promise<string | null> {
  const firebaseAuth = initFirebase();
  if (!firebaseAuth) return null;
  const user = firebaseAuth.currentUser;
  if (!user) return null;
  return user.getIdToken(/* forceRefresh= */ false);
}

/**
 * Subscribe to Firebase auth state changes.
 * Calls callback with the User object when signed in, or null when signed out.
 * Returns an unsubscribe function.
 */
export function onAuthChanged(callback: (user: User | null) => void): () => void {
  const firebaseAuth = initFirebase();
  if (!firebaseAuth) {
    // Dev mode: immediately call with a mock user
    callback({ uid: "dev-user", email: "dev@localhost" } as unknown as User);
    return () => {};
  }
  return firebaseOnAuthStateChanged(firebaseAuth, callback);
}
