import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

import 'config.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  ApiException(this.status, this.message);

  @override
  String toString() => message;
}

/// Every call to the EatFit backend goes through here.
/// It attaches the user's login token and turns errors into readable messages.
class Api {
  static String get _base => '${Config.apiUrl}/v1';

  static Map<String, String> _headers({bool json = true}) {
    final token = Supabase.instance.client.auth.currentSession?.accessToken;
    return {
      if (json) 'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Sends a request; on 401 refreshes the login once and retries.
  static Future<dynamic> _send(Future<http.Response> Function() call, {bool retried = false}) async {
    http.Response r;
    try {
      r = await call().timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw ApiException(0, 'The server took too long. Please try again.');
    } catch (_) {
      throw ApiException(0, 'Cannot reach the server. Check your internet connection.');
    }

    if (r.statusCode == 401 && !retried) {
      try {
        await Supabase.instance.client.auth.refreshSession();
        return _send(call, retried: true);
      } catch (_) {
        await Supabase.instance.client.auth.signOut();
        throw ApiException(401, 'Please sign in again.');
      }
    }

    dynamic body;
    try {
      body = r.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      body = null;
    }
    if (r.statusCode >= 400) {
      final detail = body is Map ? body['detail'] : null;
      final message = detail is String
          ? detail
          : r.statusCode == 422
              ? 'Please check the values you entered.'
              : 'Something went wrong (${r.statusCode}).';
      throw ApiException(r.statusCode, message);
    }
    return body;
  }

  static Future<dynamic> _get(String path, [Map<String, String>? query]) => _send(() =>
      http.get(Uri.parse('$_base$path').replace(queryParameters: query), headers: _headers()));

  static Future<dynamic> _post(String path, Object body) => _send(() =>
      http.post(Uri.parse('$_base$path'), headers: _headers(), body: jsonEncode(body)));

  static Future<dynamic> _put(String path, Object body) => _send(() =>
      http.put(Uri.parse('$_base$path'), headers: _headers(), body: jsonEncode(body)));

  static Future<dynamic> _delete(String path) =>
      _send(() => http.delete(Uri.parse('$_base$path'), headers: _headers()));

  // ---------------- profile ----------------
  /// Returns null if the user hasn't set up a profile yet.
  static Future<Map<String, dynamic>?> getMe() async {
    try {
      return await _get('/me');
    } on ApiException catch (e) {
      if (e.status == 404) return null;
      rethrow;
    }
  }

  static Future<Map<String, dynamic>> saveMe(Map<String, dynamic> profile) async =>
      await _put('/me', profile);

  static Future<void> deleteMe() async => await _delete('/me');

  // ---------------- a day ----------------
  static Future<Map<String, dynamic>> getDay(DateTime day) async => await _get('/days/${isoDate(day)}');

  static Future<Map<String, dynamic>> eat(DateTime day, String meal, List<Map<String, dynamic>> items) async =>
      await _post('/days/${isoDate(day)}/meals/$meal/eat', {'items': items});

  static Future<Map<String, dynamic>> skip(DateTime day, String meal, bool compensate) async =>
      await _post('/days/${isoDate(day)}/meals/$meal/skip', {'compensate': compensate});

  static Future<Map<String, dynamic>> resetMeal(DateTime day, String meal) async =>
      await _delete('/days/${isoDate(day)}/meals/$meal');

  static Future<List<dynamic>> suggestions(DateTime day) async =>
      await _get('/days/${isoDate(day)}/suggestions');

  // ---------------- foods & menus ----------------
  static Future<List<dynamic>> searchFoods(String q) async => await _get('/foods', {'q': q});

  static Future<Map<String, dynamic>> addFood(Map<String, dynamic> food) async =>
      await _post('/foods', food);

  static Future<Map<String, dynamic>> getMenu(DateTime day) async => await _get('/menus/${isoDate(day)}');

  static Future<Map<String, dynamic>> saveMenu(
          DateTime start, DateTime end, Map<String, List<String>> meals) async =>
      await _post('/menus', {'start_date': isoDate(start), 'end_date': isoDate(end), 'meals': meals});

  static Future<Map<String, dynamic>> scanMenu(String imagePath) async {
    return await _send(() async {
      final req = http.MultipartRequest('POST', Uri.parse('$_base/menus/scan'));
      req.headers.addAll(_headers(json: false));
      req.files.add(await http.MultipartFile.fromPath('file', imagePath));
      return http.Response.fromStream(await req.send());
    });
  }
}

// ---------------- small helpers ----------------
String isoDate(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String capitalize(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

/// "1.5 bowl Dal Tadka"
String itemLabel(Map item) {
  final s = (item['servings'] as num).toDouble();
  final amount = s == s.roundToDouble() ? s.toInt().toString() : s.toString();
  return '$amount ${item['unit']} ${item['name']}';
}

DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);
