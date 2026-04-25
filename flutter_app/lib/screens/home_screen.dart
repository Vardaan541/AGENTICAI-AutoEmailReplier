import "package:firebase_auth/firebase_auth.dart";
import "package:flutter/material.dart";

import "../models/email_item.dart";
import "../services/api_service.dart";
import "../services/auth_service.dart";

class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.authService,
    required this.apiService,
  });

  final AuthService authService;
  final ApiService apiService;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<EmailItem> _pending = <EmailItem>[];
  bool _loading = false;
  bool _actionInProgress = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPending();
  }

  Future<void> _loadPending() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final String? token = await widget.authService.getIdToken();
      if (token == null) {
        throw Exception("User token unavailable.");
      }
      final List<EmailItem> emails = await widget.apiService.fetchPendingEmails(token);
      if (!mounted) return;
      setState(() {
        _pending = emails;
      });
    } catch (e) {
      if (!mounted) return;
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

  Future<void> _approve(EmailItem email) async {
    setState(() {
      _actionInProgress = true;
    });
    final String? token = await widget.authService.getIdToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService.approveEmail(token, email.id);
      await _loadPending();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Approve failed: $e")),
      );
    } finally {
      if (mounted) {
        setState(() {
          _actionInProgress = false;
        });
      }
    }
  }

  Future<void> _reject(EmailItem email) async {
    setState(() {
      _actionInProgress = true;
    });
    final String? token = await widget.authService.getIdToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService.rejectEmail(token, email.id);
      await _loadPending();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Reject failed: $e")),
      );
    } finally {
      if (mounted) {
        setState(() {
          _actionInProgress = false;
        });
      }
    }
  }

  Future<void> _editAndApprove(EmailItem email) async {
    final TextEditingController controller = TextEditingController(text: email.generatedReply);
    controller.selection = TextSelection(baseOffset: 0, extentOffset: controller.text.length);
    final String? edited = await showDialog<String>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text("Edit reply"),
          content: SizedBox(
            width: 420,
            child: TextField(
              controller: controller,
              autofocus: true,
              enableInteractiveSelection: true,
              minLines: 8,
              maxLines: 14,
              textInputAction: TextInputAction.newline,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
            ),
          ),
          actions: <Widget>[
            TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
            ElevatedButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text("Send")),
          ],
        );
      },
    );

    if (edited == null || edited.isEmpty) return;
    setState(() {
      _actionInProgress = true;
    });
    final String? token = await widget.authService.getIdToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService.editAndApproveEmail(token, email.id, edited);
      await _loadPending();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Edit + approve failed: $e")),
      );
    } finally {
      if (mounted) {
        setState(() {
          _actionInProgress = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final User? user = FirebaseAuth.instance.currentUser;
    return Scaffold(
      appBar: AppBar(
        title: const Text("Pending Email Replies"),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _actionInProgress ? null : _loadPending,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _actionInProgress ? null : () => widget.authService.signOut(),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : _pending.isEmpty
                  ? Center(child: Text("No pending emails for ${user?.email ?? "user"}"))
                  : ListView.builder(
                      itemCount: _pending.length,
                      itemBuilder: (BuildContext context, int index) {
                        final EmailItem email = _pending[index];
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(email.subject, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                                const SizedBox(height: 6),
                                Text("From: ${email.sender}"),
                                Text("Class: ${email.classification} | Urgency: ${email.urgency}"),
                                Text("Intent: ${email.intent}"),
                                Text("Required action: ${email.requiredAction}"),
                                const SizedBox(height: 8),
                                const Text("Original Email", style: TextStyle(fontWeight: FontWeight.bold)),
                                Text(email.body, maxLines: 4, overflow: TextOverflow.ellipsis),
                                const SizedBox(height: 8),
                                const Text("Generated Reply", style: TextStyle(fontWeight: FontWeight.bold)),
                                Text(email.generatedReply, maxLines: 5, overflow: TextOverflow.ellipsis),
                                const SizedBox(height: 10),
                                Wrap(
                                  spacing: 8,
                                  children: <Widget>[
                                    ElevatedButton(
                                      onPressed: _actionInProgress ? null : () => _approve(email),
                                      child: const Text("Approve"),
                                    ),
                                    ElevatedButton(
                                      onPressed: _actionInProgress ? null : () => _editAndApprove(email),
                                      child: const Text("Edit + Approve"),
                                    ),
                                    OutlinedButton(
                                      onPressed: _actionInProgress ? null : () => _reject(email),
                                      child: const Text("Reject"),
                                    ),
                                  ],
                                )
                              ],
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}
