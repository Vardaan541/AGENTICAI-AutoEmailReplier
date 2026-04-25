import "dart:convert";

import "package:http/http.dart" as http;

import "../models/email_item.dart";

class ApiService {
  ApiService({required this.baseUrl});

  final String baseUrl;

  Map<String, String> _headers(String token, {String? gmailAccessToken}) {
    final Map<String, String> headers = <String, String>{
      "Content-Type": "application/json",
      "Authorization": "Bearer $token",
    };
    if (gmailAccessToken != null && gmailAccessToken.isNotEmpty) {
      headers["x-gmail-access-token"] = gmailAccessToken;
    }
    return headers;
  }

  Future<void> connectGmailToken(String token, String gmailAccessToken) async {
    final response = await http.post(
      Uri.parse("$baseUrl/auth/gmail/connect"),
      headers: _headers(token),
      body: jsonEncode(<String, dynamic>{"access_token": gmailAccessToken}),
    );
    if (response.statusCode != 200) {
      throw Exception("Failed to connect Gmail token: ${response.body}");
    }
  }

  Future<void> exchangeGmailAuthCode(String token, String serverAuthCode) async {
    final response = await http.post(
      Uri.parse("$baseUrl/auth/gmail/exchange-code"),
      headers: _headers(token),
      body: jsonEncode(<String, dynamic>{"server_auth_code": serverAuthCode}),
    );
    if (response.statusCode != 200) {
      throw Exception("Failed to exchange Gmail auth code: ${response.body}");
    }
  }

  Future<void> pollOnce(String token, String gmailAccessToken) async {
    final response = await http.post(
      Uri.parse("$baseUrl/poll-once"),
      headers: _headers(token, gmailAccessToken: gmailAccessToken),
    );
    if (response.statusCode != 200) {
      throw Exception("Failed to poll inbox: ${response.body}");
    }
  }

  Future<List<EmailItem>> fetchPendingEmails(String token, {String? gmailAccessToken}) async {
    final response = await http.get(
      Uri.parse("$baseUrl/pending"),
      headers: _headers(token, gmailAccessToken: gmailAccessToken),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to load pending emails: ${response.body}");
    }
    final List<dynamic> body = jsonDecode(response.body) as List<dynamic>;
    return body
        .map((dynamic item) => EmailItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> approveEmail(String token, int emailId, {String? gmailAccessToken}) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/approve"),
      headers: _headers(token, gmailAccessToken: gmailAccessToken),
    );
    if (response.statusCode != 200) {
      throw Exception("Approve failed: ${response.body}");
    }
  }

  Future<void> rejectEmail(String token, int emailId, {String? gmailAccessToken}) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/reject"),
      headers: _headers(token, gmailAccessToken: gmailAccessToken),
    );
    if (response.statusCode != 200) {
      throw Exception("Reject failed: ${response.body}");
    }
  }

  Future<void> editAndApproveEmail(
    String token,
    int emailId,
    String replyText, {
    String? gmailAccessToken,
  }) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/edit-and-approve"),
      headers: _headers(token, gmailAccessToken: gmailAccessToken),
      body: jsonEncode({"reply_text": replyText}),
    );
    if (response.statusCode != 200) {
      throw Exception("Edit and approve failed: ${response.body}");
    }
  }
}
