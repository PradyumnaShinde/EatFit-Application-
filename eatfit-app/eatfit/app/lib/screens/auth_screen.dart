import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../widgets.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool signUp = false;
  bool busy = false;

  GoTrueClient get _auth => Supabase.instance.client.auth;

  Future<void> _submit() async {
    final e = email.text.trim();
    if (!e.contains('@') || password.text.length < 8) {
      toast(context, 'Enter a valid email and a password of at least 8 characters');
      return;
    }
    setState(() => busy = true);
    try {
      if (signUp) {
        final res = await _auth.signUp(email: e, password: password.text);
        if (res.session == null && mounted) {
          toast(context, 'Check your email to confirm your account, then sign in.');
          setState(() => signUp = false);
        }
      } else {
        await _auth.signInWithPassword(email: e, password: password.text);
      }
      // On success AuthGate rebuilds automatically.
    } on AuthException catch (err) {
      if (mounted) toast(context, err.message);
    } catch (_) {
      if (mounted) toast(context, 'Could not connect. Check your internet.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _forgot() async {
    final e = email.text.trim();
    if (!e.contains('@')) {
      toast(context, 'Type your email first');
      return;
    }
    try {
      await _auth.resetPasswordForEmail(e);
      if (mounted) toast(context, 'Password reset email sent');
    } on AuthException catch (err) {
      if (mounted) toast(context, err.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Text('EatFit',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              const Text('Eat right from the menu you actually have.', textAlign: TextAlign.center),
              const SizedBox(height: 32),
              TextField(
                controller: email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: password,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: busy ? null : _submit,
                child: Text(signUp ? 'Create account' : 'Sign in'),
              ),
              TextButton(
                onPressed: busy ? null : () => setState(() => signUp = !signUp),
                child: Text(signUp ? 'Have an account? Sign in' : 'New here? Create an account'),
              ),
              if (!signUp) TextButton(onPressed: busy ? null : _forgot, child: const Text('Forgot password?')),
              const SizedBox(height: 24),
              const Text(disclaimer, textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: Colors.grey)),
            ]),
          ),
        ),
      ),
    );
  }
}
