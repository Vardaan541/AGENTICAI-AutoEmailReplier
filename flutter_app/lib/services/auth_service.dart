import "package:firebase_auth/firebase_auth.dart";
import "package:google_sign_in/google_sign_in.dart";

class AuthService {
  final FirebaseAuth _firebaseAuth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: <String>["email"]);

  Stream<User?> authStateChanges() => _firebaseAuth.authStateChanges();

  Future<void> signInWithGoogle() async {
    final GoogleSignInAccount? account = await _googleSignIn.signIn();
    if (account == null) {
      throw Exception("Google sign-in cancelled.");
    }
    final GoogleSignInAuthentication googleAuth = await account.authentication;

    final OAuthCredential credential = GoogleAuthProvider.credential(
      idToken: googleAuth.idToken,
    );
    await _firebaseAuth.signInWithCredential(credential);
  }

  Future<String?> getIdToken() async {
    return _firebaseAuth.currentUser?.getIdToken();
  }

  Future<void> signOut() async {
    await _firebaseAuth.signOut();
    await _googleSignIn.signOut();
  }
}
