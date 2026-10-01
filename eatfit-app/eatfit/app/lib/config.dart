/// Values injected at build time:
///   flutter run --dart-define-from-file=env.json
/// (copy env.example.json to env.json and fill it in; env.json is git-ignored)
class Config {
  static const apiUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8000');
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

  static bool get isConfigured => supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}
