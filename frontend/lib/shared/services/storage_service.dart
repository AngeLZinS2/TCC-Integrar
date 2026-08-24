import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_model.dart';

class StorageService {
  static const String _keyAccessToken = 'auth_access_token';
  static const String _keyRefreshToken = 'auth_refresh_token';
  static const String _keyUserData = 'auth_user_data';

  // Access Token
  Future<void> saveAccessToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyAccessToken, token);
  }

  Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyAccessToken);
  }

  // Refresh Token
  Future<void> saveRefreshToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyRefreshToken, token);
  }

  Future<String?> getRefreshToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyRefreshToken);
  }

  // User Profile
  Future<void> saveUser(UserModel user) async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = jsonEncode(user.toJson());
    await prefs.setString(_keyUserData, jsonString);
  }

  Future<UserModel?> getUser() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_keyUserData);
    if (jsonString == null) return null;
    try {
      final Map<String, dynamic> data = jsonDecode(jsonString);
      return UserModel.fromJson(data);
    } catch (_) {
      return null;
    }
  }

  // Clear all tokens on logout
  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyAccessToken);
    await prefs.remove(_keyRefreshToken);
    await prefs.remove(_keyUserData);
  }
}
