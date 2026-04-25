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
    required this.onToggleTheme,
    required this.isDarkMode,
  });

  final AuthService authService;
  final ApiService apiService;
  final VoidCallback onToggleTheme;
  final bool isDarkMode;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<EmailItem> _pending = <EmailItem>[];
  bool _loading = false;
  bool _actionInProgress = false;
  String? _error;
  final TextEditingController _searchController = TextEditingController();
  String _selectedUrgency = "All";

  static const List<String> _urgencyOptions = <String>[
    "All",
    "High",
    "Medium",
    "Low",
  ];

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
      final String? serverAuthCode =
          await widget.authService.getServerAuthCode();
      if (serverAuthCode != null && serverAuthCode.isNotEmpty) {
        try {
          await widget.apiService.exchangeGmailAuthCode(token, serverAuthCode);
        } catch (_) {
          // Fallback to short-lived access token path.
        }
      }
      final String? gmailAccessToken =
          await widget.authService.getGmailAccessToken();
      if (gmailAccessToken == null || gmailAccessToken.isEmpty) {
        throw Exception(
            "Gmail access token unavailable. Please sign in again.");
      }
      await widget.apiService.connectGmailToken(token, gmailAccessToken);
      await widget.apiService.pollOnce(token, gmailAccessToken);
      final List<EmailItem> emails = await widget.apiService.fetchPendingEmails(
        token,
        gmailAccessToken: gmailAccessToken,
      );
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

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _approve(EmailItem email) async {
    setState(() {
      _actionInProgress = true;
    });
    final String? token = await widget.authService.getIdToken();
    final String? gmailAccessToken =
        await widget.authService.getGmailAccessToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    if (gmailAccessToken == null || gmailAccessToken.isEmpty) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService
          .approveEmail(token, email.id, gmailAccessToken: gmailAccessToken);
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
    final String? gmailAccessToken =
        await widget.authService.getGmailAccessToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    if (gmailAccessToken == null || gmailAccessToken.isEmpty) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService
          .rejectEmail(token, email.id, gmailAccessToken: gmailAccessToken);
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
    final TextEditingController controller =
        TextEditingController(text: email.generatedReply);
    controller.selection =
        TextSelection(baseOffset: 0, extentOffset: controller.text.length);
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
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text("Cancel")),
            ElevatedButton(
                onPressed: () => Navigator.pop(context, controller.text.trim()),
                child: const Text("Send")),
          ],
        );
      },
    );

    if (edited == null || edited.isEmpty) return;
    setState(() {
      _actionInProgress = true;
    });
    final String? token = await widget.authService.getIdToken();
    final String? gmailAccessToken =
        await widget.authService.getGmailAccessToken();
    if (token == null) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    if (gmailAccessToken == null || gmailAccessToken.isEmpty) {
      setState(() {
        _actionInProgress = false;
      });
      return;
    }
    try {
      await widget.apiService.editAndApproveEmail(
        token,
        email.id,
        edited,
        gmailAccessToken: gmailAccessToken,
      );
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
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;
    final String query = _searchController.text.trim().toLowerCase();
    final List<EmailItem> filteredEmails = _pending.where((EmailItem email) {
      final bool urgencyMatch = _selectedUrgency == "All" ||
          email.urgency.toLowerCase() == _selectedUrgency.toLowerCase();
      final bool searchMatch = query.isEmpty ||
          email.subject.toLowerCase().contains(query) ||
          email.sender.toLowerCase().contains(query) ||
          email.intent.toLowerCase().contains(query);
      return urgencyMatch && searchMatch;
    }).toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text("Pending Reply Queue"),
        actions: <Widget>[
          IconButton(
            icon: Icon(
              widget.isDarkMode
                  ? Icons.light_mode_rounded
                  : Icons.dark_mode_rounded,
            ),
            onPressed: widget.onToggleTheme,
            tooltip: widget.isDarkMode
                ? "Switch to light mode"
                : "Switch to dark mode",
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _actionInProgress ? null : _loadPending,
            tooltip: "Refresh",
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed:
                _actionInProgress ? null : () => widget.authService.signOut(),
            tooltip: "Logout",
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadPending,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
          children: <Widget>[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      "Welcome, ${user?.displayName ?? user?.email ?? "User"}",
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      "${_pending.length} pending emails need your decision.",
                      style: TextStyle(color: colors.onSurfaceVariant),
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _searchController,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: "Search by sender, subject, or intent",
                        prefixIcon: const Icon(Icons.search_rounded),
                        suffixIcon: _searchController.text.isEmpty
                            ? null
                            : IconButton(
                                icon: const Icon(Icons.close_rounded),
                                onPressed: () {
                                  _searchController.clear();
                                  setState(() {});
                                },
                              ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Wrap(
                        spacing: 8,
                        children: _urgencyOptions.map((String urgency) {
                          return ChoiceChip(
                            label: Text(urgency),
                            selected: _selectedUrgency == urgency,
                            onSelected: (_) {
                              setState(() {
                                _selectedUrgency = urgency;
                              });
                            },
                          );
                        }).toList(),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 20),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 20),
                child: Center(
                  child: Text(
                    _error!,
                    style: TextStyle(color: colors.error),
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            else if (filteredEmails.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 20),
                child: Center(
                  child: Text(
                    _pending.isEmpty
                        ? "No pending emails for ${user?.email ?? "user"}"
                        : "No emails match your filters.",
                    textAlign: TextAlign.center,
                    style: TextStyle(color: colors.onSurfaceVariant),
                  ),
                ),
              )
            else
              ...filteredEmails.map((EmailItem email) {
                return _EmailCard(
                  email: email,
                  actionInProgress: _actionInProgress,
                  onApprove: () => _approve(email),
                  onEditApprove: () => _editAndApprove(email),
                  onReject: () => _reject(email),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _EmailCard extends StatelessWidget {
  const _EmailCard({
    required this.email,
    required this.actionInProgress,
    required this.onApprove,
    required this.onEditApprove,
    required this.onReject,
  });

  final EmailItem email;
  final bool actionInProgress;
  final VoidCallback onApprove;
  final VoidCallback onEditApprove;
  final VoidCallback onReject;

  Color _urgencyColor(ColorScheme colors, String urgency) {
    switch (urgency.toLowerCase()) {
      case "high":
        return colors.errorContainer;
      case "medium":
        return colors.tertiaryContainer;
      default:
        return colors.primaryContainer;
    }
  }

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final ColorScheme colors = theme.colorScheme;

    return Card(
      margin: const EdgeInsets.only(top: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Text(
                    email.subject,
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
                const SizedBox(width: 8),
                Chip(
                  backgroundColor: _urgencyColor(colors, email.urgency),
                  label: Text(email.urgency.toUpperCase()),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text("From ${email.sender}",
                style: TextStyle(color: colors.onSurfaceVariant)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                _MetaTag(label: "Class", value: email.classification),
                _MetaTag(label: "Intent", value: email.intent),
                _MetaTag(label: "Action", value: email.requiredAction),
              ],
            ),
            const SizedBox(height: 10),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              title: const Text("Original email"),
              collapsedIconColor: colors.onSurfaceVariant,
              iconColor: colors.primary,
              children: <Widget>[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(email.body),
                ),
              ],
            ),
            ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              title: const Text("Generated reply"),
              collapsedIconColor: colors.onSurfaceVariant,
              iconColor: colors.primary,
              initiallyExpanded: true,
              children: <Widget>[
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(email.generatedReply),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                FilledButton.icon(
                  onPressed: actionInProgress ? null : onApprove,
                  icon: const Icon(Icons.check_circle_outline_rounded),
                  label: const Text("Approve"),
                ),
                OutlinedButton.icon(
                  onPressed: actionInProgress ? null : onEditApprove,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text("Edit + Send"),
                ),
                OutlinedButton.icon(
                  onPressed: actionInProgress ? null : onReject,
                  icon: const Icon(Icons.close_rounded),
                  label: const Text("Reject"),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MetaTag extends StatelessWidget {
  const _MetaTag({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: colors.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        "$label: $value",
        style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12),
      ),
    );
  }
}
