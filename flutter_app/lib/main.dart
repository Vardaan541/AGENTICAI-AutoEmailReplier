import "package:firebase_auth/firebase_auth.dart";
import "package:firebase_core/firebase_core.dart";
import "package:flutter/material.dart";

import "screens/home_screen.dart";
import "screens/login_screen.dart";
import "services/api_service.dart";
import "services/auth_service.dart";

const String apiBaseUrl = String.fromEnvironment(
  "API_BASE_URL",
  defaultValue: "https://email-agentic-api-187775668985.asia-south1.run.app",
);
const String googleServerClientId = String.fromEnvironment(
  "GOOGLE_SERVER_CLIENT_ID",
  defaultValue:
      "187775668985-9bno36ui5uitu1hkjdcdrubr1ie9l9n1.apps.googleusercontent.com",
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
  late final AuthService _authService =
      AuthService(serverClientId: googleServerClientId);
  late final ApiService _apiService = ApiService(baseUrl: apiBaseUrl);
  ThemeMode _themeMode = ThemeMode.dark;

  ThemeData _buildTheme(Brightness brightness) {
    final bool isDark = brightness == Brightness.dark;
    final ColorScheme colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF4F46E5),
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor:
          isDark ? const Color(0xFF0A1021) : const Color(0xFFF3F6FF),
      cardTheme: CardThemeData(
        color: isDark ? const Color(0xFF121A33) : Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        backgroundColor: Colors.transparent,
        scrolledUnderElevation: 0,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size(0, 44),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? const Color(0xFF111936) : const Color(0xFFF8FAFF),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colorScheme.outlineVariant),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(
              color: colorScheme.outlineVariant.withValues(alpha: 0.45)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: colorScheme.primary, width: 1.6),
        ),
      ),
    );
  }

  void _toggleTheme() {
    setState(() {
      _themeMode =
          _themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Email Agentic AI",
      debugShowCheckedModeBanner: false,
      theme: _buildTheme(Brightness.light),
      darkTheme: _buildTheme(Brightness.dark),
      themeMode: _themeMode,
      home: StreamBuilder<User?>(
        stream: _authService.authStateChanges(),
        builder: (BuildContext context, AsyncSnapshot<User?> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
                body: Center(child: CircularProgressIndicator()));
          }
          if (snapshot.data == null) {
            return LoginScreen(
              authService: _authService,
              onToggleTheme: _toggleTheme,
              isDarkMode: _themeMode == ThemeMode.dark,
            );
          }
          return HomeScreen(
            authService: _authService,
            apiService: _apiService,
            onToggleTheme: _toggleTheme,
            isDarkMode: _themeMode == ThemeMode.dark,
          );
        },
      ),
    );
  }
}
