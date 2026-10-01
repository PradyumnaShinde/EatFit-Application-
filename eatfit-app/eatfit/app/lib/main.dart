import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'api.dart';
import 'config.dart';
import 'screens/auth_screen.dart';
import 'screens/home_shell.dart';
import 'screens/profile_screen.dart';
import 'widgets.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (Config.isConfigured) {
    await Supabase.initialize(url: Config.supabaseUrl, anonKey: Config.supabaseAnonKey);
  }
  runApp(const EatFitApp());
}

class EatFitApp extends StatelessWidget {
  const EatFitApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EatFit',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF2E9E83), useMaterial3: true),
      home: Config.isConfigured
          ? const AuthGate()
          : const Scaffold(
              body: Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('App not configured.\nRun with --dart-define-from-file=env.json',
                      textAlign: TextAlign.center),
                ),
              ),
            ),
    );
  }
}

/// Signed out -> login screen. Signed in -> onboarding (first time) or the app.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<AuthState>(
      stream: Supabase.instance.client.auth.onAuthStateChange,
      builder: (context, _) {
        final session = Supabase.instance.client.auth.currentSession;
        if (session == null) return const AuthScreen();
        return OnboardingGate(key: ValueKey(session.user.id));
      },
    );
  }
}

class OnboardingGate extends StatefulWidget {
  const OnboardingGate({super.key});

  @override
  State<OnboardingGate> createState() => _OnboardingGateState();
}

class _OnboardingGateState extends State<OnboardingGate> {
  bool? hasProfile;
  String? error;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    setState(() => error = null);
    try {
      final me = await Api.getMe();
      if (mounted) setState(() => hasProfile = me != null);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) return Scaffold(body: ErrorView(message: error!, onRetry: _check));
    if (hasProfile == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (!hasProfile!) {
      return Scaffold(
        body: SafeArea(
          child: ProfileScreen(onboarding: true, onSaved: () => setState(() => hasProfile = true)),
        ),
      );
    }
    return const HomeShell();
  }
}
