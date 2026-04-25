class EmailItem {
  final int id;
  final String sender;
  final String subject;
  final String body;
  final String generatedReply;
  final String approvalStatus;
  final String classification;
  final String intent;
  final String urgency;
  final String requiredAction;

  EmailItem({
    required this.id,
    required this.sender,
    required this.subject,
    required this.body,
    required this.generatedReply,
    required this.approvalStatus,
    required this.classification,
    required this.intent,
    required this.urgency,
    required this.requiredAction,
  });

  factory EmailItem.fromJson(Map<String, dynamic> json) {
    return EmailItem(
      id: json["id"] as int,
      sender: (json["sender"] ?? "") as String,
      subject: (json["subject"] ?? "") as String,
      body: (json["body"] ?? "") as String,
      generatedReply: (json["generated_reply"] ?? "") as String,
      approvalStatus: (json["approval_status"] ?? "") as String,
      classification: (json["classification"] ?? "") as String,
      intent: (json["intent"] ?? "") as String,
      urgency: (json["urgency"] ?? "") as String,
      requiredAction: (json["required_action"] ?? "") as String,
    );
  }
}
