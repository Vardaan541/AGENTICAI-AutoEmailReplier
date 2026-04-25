import "dart:convert";

import "package:http/http.dart" as http;

import "../models/email_item.dart";

class ApiService {
  ApiService({required this.baseUrl});

  final String baseUrl;

  Map<String, String> _headers(String token) {
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer $token",
    };
  }

  Future<List<EmailItem>> fetchPendingEmails(String token) async {
    final response = await http.get(
      Uri.parse("$baseUrl/pending"),
      headers: _headers(token),
    );

    if (response.statusCode != 200) {
      throw Exception("Failed to load pending emails: ${response.body}");
    }
    final List<dynamic> body = jsonDecode(response.body) as List<dynamic>;
    return body
        .map((dynamic item) => EmailItem.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> approveEmail(String token, int emailId) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/approve"),
      headers: _headers(token),
    );
    if (response.statusCode != 200) {
      throw Exception("Approve failed: ${response.body}");
    }
  }

  Future<void> rejectEmail(String token, int emailId) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/reject"),
      headers: _headers(token),
    );
    if (response.statusCode != 200) {
      throw Exception("Reject failed: ${response.body}");
    }
  }

  Future<void> editAndApproveEmail(String token, int emailId, String replyText) async {
    final response = await http.post(
      Uri.parse("$baseUrl/emails/$emailId/edit-and-approve"),
      headers: _headers(token),
      body: jsonEncode({"reply_text": replyText}),
    );
    if (response.statusCode != 200) {
      throw Exception("Edit and approve failed: ${response.body}");
    }
  }
}
