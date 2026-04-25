import "package:firebase_auth/firebase_auth.dart";
import "package:firebase_core/firebase_core.dart";
import "package:flutter/material.dart";

import "screens/home_screen.dart";
import "screens/login_screen.dart";
import "services/api_service.dart";
import "services/auth_service.dart";

const String apiBaseUrl = String.fromEnvironment(
  "API_BASE_URL",
  defaultValue: "https://email-agentic-api-sslf5kksaq-el.a.run.app",
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const EmailAgenticAiApp());
}

class EmailAgenticAiApp extends StatefulWidget {
  const EmailAgenticAiApp({super.key});

  @override
  State<EmailAgenticAiApp> createState() => _EmailAgenticAiAppState();
}

class _EmailAgenticAiAppState extends State<EmailAgenticAiApp> {
  final AuthService _authService = AuthService();
  late final ApiService _apiService = ApiService(baseUrl: apiBaseUrl);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Email Agentic AI",
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: StreamBuilder<User?>(
        stream: _authService.authStateChanges(),
        builder: (BuildContext context, AsyncSnapshot<User?> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          if (snapshot.data == null) {
            return LoginScreen(authService: _authService);
          }
          return HomeScreen(authService: _authService, apiService: _apiService);
        },
      ),
    );
  }
}
