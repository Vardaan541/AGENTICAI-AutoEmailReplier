import "package:flutter/material.dart";

import "../services/auth_service.dart";

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.authService,
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  final AuthService authService;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _loading = false;
  String? _error;

  Future<void> _signIn() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.authService.signInWithGoogle();
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;

    return Scaffold(
      body: Stack(
        children: <Widget>[
          const _LoginBackground(),
          Positioned(
            top: 12,
            right: 12,
            child: SafeArea(
              child: IconButton.filledTonal(
                onPressed: widget.onToggleTheme,
                tooltip: widget.isDarkMode
                    ? "Switch to light mode"
                    : "Switch to dark mode",
                icon: Icon(
                  widget.isDarkMode
                      ? Icons.light_mode_rounded
                      : Icons.dark_mode_rounded,
                ),
              ),
            ),
          ),
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 440),
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color:
                                colors.primaryContainer.withValues(alpha: 0.5),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: const Text("Smart Reply Command Center"),
                        ),
                        const SizedBox(height: 16),
                        const Text(
                          "Email Agentic AI",
                          style: TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.w700,
                              height: 1.2),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          "Review AI-generated replies quickly, keep approvals in control, and respond with confidence.",
                          style: TextStyle(
                              color: colors.onSurfaceVariant, height: 1.35),
                        ),
                        const SizedBox(height: 22),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _loading ? null : _signIn,
                            icon: _loading
                                ? const SizedBox(
                                    height: 16,
                                    width: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2),
                                  )
                                : const Icon(Icons.login_rounded),
                            label: Text(_loading
                                ? "Signing in..."
                                : "Continue with Google"),
                          ),
                        ),
                        const SizedBox(height: 14),
                        Text(
                          "One-tap sign in. Your Gmail access is used only to fetch and process pending replies.",
                          style: TextStyle(
                              color: colors.onSurfaceVariant, fontSize: 12.5),
                        ),
                        if (_error != null) ...<Widget>[
                          const SizedBox(height: 12),
                          Text(_error!, style: TextStyle(color: colors.error)),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LoginBackground extends StatelessWidget {
  const _LoginBackground();

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? <Color>[
                  const Color(0xFF060C1D),
                  const Color(0xFF151B33),
                  const Color(0xFF111A3A),
                ]
              : <Color>[
                  const Color(0xFFEAF1FF),
                  const Color(0xFFF5F8FF),
                  const Color(0xFFEFF3FF),
                ],
        ),
      ),
      child: Stack(
        children: <Widget>[
          Positioned(
            top: -80,
            right: -60,
            child: Container(
              width: 240,
              height: 240,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: <Color>[
                  isDark ? const Color(0x334F46E5) : const Color(0x554F46E5),
                  const Color(0x00000000),
                ]),
              ),
            ),
          ),
          Positioned(
            bottom: -60,
            left: -30,
            child: Container(
              width: 220,
              height: 220,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(colors: <Color>[
                  isDark ? const Color(0x3338BDF8) : const Color(0x5538BDF8),
                  const Color(0x00000000),
                ]),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
