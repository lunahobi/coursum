import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:html/dom.dart' as dom;
import 'package:html/parser.dart' as html_parser;
import 'package:url_launcher/url_launcher.dart';

import '../app_localization.dart';
import '../player/lesson_video_player.dart';
import 'lesson_media_frame.dart';

typedef ResolveLessonMediaUrl = String Function(String? rawUrl);
typedef ResolveLessonMediaHeaders = Map<String, String>? Function(
    String resolvedUrl);

class LessonHtmlBlock extends StatefulWidget {
  const LessonHtmlBlock({
    super.key,
    required this.html,
    required this.resolveUrl,
    required this.resolveHeaders,
    required this.savedVideoPositionFor,
    required this.onVideoPositionChanged,
  });

  final String html;
  final ResolveLessonMediaUrl resolveUrl;
  final ResolveLessonMediaHeaders resolveHeaders;
  final int Function(String videoUrl) savedVideoPositionFor;
  final void Function(String videoUrl, int seconds) onVideoPositionChanged;

  @override
  State<LessonHtmlBlock> createState() => _LessonHtmlBlockState();
}

class _LessonHtmlBlockState extends State<LessonHtmlBlock> {
  final List<TapGestureRecognizer> _linkRecognizers = [];

  @override
  void dispose() {
    for (final recognizer in _linkRecognizers) {
      recognizer.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    for (final recognizer in _linkRecognizers) {
      recognizer.dispose();
    }
    _linkRecognizers.clear();
    final fragment = html_parser.parseFragment(widget.html);
    final children = _buildChildren(context, fragment.nodes);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: children.isEmpty ? [const SizedBox.shrink()] : children,
    );
  }

  List<Widget> _buildChildren(BuildContext context, List<dom.Node> nodes) {
    final widgets = <Widget>[];
    for (final node in nodes) {
      final widget = _buildNode(context, node);
      if (widget == null) {
        continue;
      }
      widgets.add(widget);
    }
    return widgets;
  }

  Widget? _buildNode(BuildContext context, dom.Node node) {
    if (node is dom.Text) {
      final text = node.text.trim();
      if (text.isEmpty) {
        return null;
      }
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Text(text, style: Theme.of(context).textTheme.bodyLarge),
      );
    }
    if (node is! dom.Element) {
      return null;
    }
    final tag = node.localName?.toLowerCase() ?? 'div';
    switch (tag) {
      case 'h1':
      case 'h2':
      case 'h3':
      case 'h4':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12, top: 6),
          child: Text(
            node.text.trim(),
            style: _headingStyle(context, tag),
          ),
        );
      case 'p':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text.rich(
            TextSpan(
              style: Theme.of(context).textTheme.bodyLarge,
              children: _buildInlineSpans(context, node.nodes),
            ),
          ),
        );
      case 'a':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text.rich(
            TextSpan(
              style: Theme.of(context).textTheme.bodyLarge,
              children: [
                _buildLinkSpan(
                    context, node, Theme.of(context).textTheme.bodyLarge),
              ],
            ),
          ),
        );
      case 'ul':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: node.children
                .where((element) => element.localName == 'li')
                .map((element) =>
                    _buildListItem(context, element, ordered: false))
                .toList(),
          ),
        );
      case 'ol':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: node.children
                .where((element) => element.localName == 'li')
                .toList()
                .asMap()
                .entries
                .map((entry) => _buildListItem(context, entry.value,
                    ordered: true, index: entry.key + 1))
                .toList(),
          ),
        );
      case 'blockquote':
        return Container(
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(16),
            border: Border(
              left: BorderSide(
                width: 4,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
          child: Text.rich(
            TextSpan(
              style: Theme.of(context).textTheme.bodyLarge,
              children: _buildInlineSpans(context, node.nodes),
            ),
          ),
        );
      case 'pre':
        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 14),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(16),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Text(
              node.text.trim(),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontFamily: 'monospace',
                    height: 1.5,
                  ),
            ),
          ),
        );
      case 'img':
        return _buildImage(
            context, node.attributes['src'], node.attributes['alt']);
      case 'video':
        return _buildVideo(context, node);
      case 'table':
        return _buildTable(context, node);
      case 'div':
      case 'span':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: _buildChildren(context, node.nodes),
        );
      case 'hr':
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 10),
          child: Divider(height: 1),
        );
      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: _buildChildren(context, node.nodes),
        );
    }
  }

  TextStyle? _headingStyle(BuildContext context, String tag) {
    switch (tag) {
      case 'h1':
        return Theme.of(context).textTheme.headlineMedium;
      case 'h2':
        return Theme.of(context).textTheme.headlineSmall;
      case 'h3':
        return Theme.of(context).textTheme.titleLarge;
      default:
        return Theme.of(context).textTheme.titleMedium;
    }
  }

  List<InlineSpan> _buildInlineSpans(BuildContext context, List<dom.Node> nodes,
      {TextStyle? style}) {
    final baseStyle = style ?? Theme.of(context).textTheme.bodyLarge;
    final spans = <InlineSpan>[];
    for (final node in nodes) {
      if (node is dom.Text) {
        if (node.text.isEmpty) {
          continue;
        }
        spans.add(TextSpan(text: node.text, style: baseStyle));
        continue;
      }
      if (node is! dom.Element) {
        continue;
      }
      final tag = node.localName?.toLowerCase() ?? 'span';
      switch (tag) {
        case 'strong':
        case 'b':
          spans.add(
            TextSpan(
              style: baseStyle?.copyWith(fontWeight: FontWeight.w700),
              children: _buildInlineSpans(context, node.nodes,
                  style: baseStyle?.copyWith(fontWeight: FontWeight.w700)),
            ),
          );
          break;
        case 'em':
        case 'i':
          spans.add(
            TextSpan(
              style: baseStyle?.copyWith(fontStyle: FontStyle.italic),
              children: _buildInlineSpans(context, node.nodes,
                  style: baseStyle?.copyWith(fontStyle: FontStyle.italic)),
            ),
          );
          break;
        case 'u':
          spans.add(
            TextSpan(
              style: baseStyle?.copyWith(decoration: TextDecoration.underline),
              children: _buildInlineSpans(context, node.nodes,
                  style: baseStyle?.copyWith(
                      decoration: TextDecoration.underline)),
            ),
          );
          break;
        case 'code':
          spans.add(
            WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: 2),
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  node.text,
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(fontFamily: 'monospace'),
                ),
              ),
            ),
          );
          break;
        case 'br':
          spans.add(const TextSpan(text: '\n'));
          break;
        case 'a':
          spans.add(_buildLinkSpan(context, node, baseStyle));
          break;
        case 'img':
          spans.add(
            WidgetSpan(
              alignment: PlaceholderAlignment.middle,
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: 320,
                    minHeight: 120,
                  ),
                  child: _buildImage(
                      context, node.attributes['src'], node.attributes['alt']),
                ),
              ),
            ),
          );
          break;
        default:
          spans
              .addAll(_buildInlineSpans(context, node.nodes, style: baseStyle));
      }
    }
    return spans;
  }

  InlineSpan _buildLinkSpan(
      BuildContext context, dom.Element node, TextStyle? baseStyle) {
    final rawHref = node.attributes['href'];
    final resolvedHref = widget.resolveUrl(rawHref);
    final label = _normalizedLinkText(node) ??
        _fallbackLinkLabel(
            rawHref?.trim().isNotEmpty == true ? rawHref! : resolvedHref);
    final linkStyle = baseStyle?.copyWith(
      color: Theme.of(context).colorScheme.primary,
      decoration: TextDecoration.underline,
      decorationColor: Theme.of(context).colorScheme.primary,
    );
    final recognizer = TapGestureRecognizer()
      ..onTap = () => _openLink(context, resolvedHref);
    _linkRecognizers.add(recognizer);
    return TextSpan(
      text: label,
      style: linkStyle,
      recognizer: recognizer,
    );
  }

  String? _normalizedLinkText(dom.Element node) {
    final text = node.text.replaceAll(RegExp(r'\s+'), ' ').trim();
    return text.isEmpty ? null : text;
  }

  String _fallbackLinkLabel(String rawUrl) {
    final trimmed = rawUrl.trim();
    if (trimmed.isEmpty) {
      return 'Link';
    }
    final uri = Uri.tryParse(trimmed);
    if (uri != null && uri.pathSegments.isNotEmpty) {
      return uri.pathSegments.last;
    }
    return trimmed;
  }

  Future<void> _openLink(BuildContext context, String? rawUrl) async {
    final uri = _parseLaunchUri(rawUrl);
    if (uri != null) {
      if (await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        return;
      }
      if (await launchUrl(uri, mode: LaunchMode.platformDefault)) {
        return;
      }
    }
    if (context.mounted) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(content: Text(context.strings.linkOpenFailed)),
      );
    }
  }

  Uri? _parseLaunchUri(String? rawUrl) {
    final trimmed = rawUrl?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    return Uri.tryParse(Uri.encodeFull(trimmed));
  }

  Widget _buildListItem(BuildContext context, dom.Element element,
      {required bool ordered, int? index}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 5, right: 8),
            child: Text(
              ordered ? '${index ?? 1}.' : '•',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
          Expanded(
            child: Text.rich(
              TextSpan(
                style: Theme.of(context).textTheme.bodyLarge,
                children: _buildInlineSpans(context, element.nodes),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImage(BuildContext context, String? rawUrl, String? altText) {
    final imageUrl = widget.resolveUrl(rawUrl);
    final imageHeaders = widget.resolveHeaders(imageUrl);
    return LessonMediaFrame(
      backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Image.network(
        imageUrl,
        fit: BoxFit.contain,
        headers: imageHeaders,
        loadingBuilder: (context, child, progress) {
          if (progress == null) {
            return child;
          }
          return const Center(child: CircularProgressIndicator());
        },
        errorBuilder: (_, __, ___) => Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              altText?.trim().isNotEmpty == true
                  ? altText!
                  : context.strings.imageUnavailable,
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildVideo(BuildContext context, dom.Element element) {
    final directSrc = element.attributes['src'];
    final nestedSource = element.children.firstWhere(
      (child) =>
          child.localName == 'source' &&
          (child.attributes['src']?.isNotEmpty ?? false),
      orElse: () => dom.Element.tag('empty'),
    );
    final sourceUrl = directSrc ?? nestedSource.attributes['src'];
    final videoUrl = widget.resolveUrl(sourceUrl);
    return InlineVideoPanel(
      key: ValueKey('html-video-$videoUrl'),
      url: videoUrl,
      title: element.attributes['title'] ?? context.strings.lessonVideo,
      initialPositionSeconds: widget.savedVideoPositionFor(videoUrl),
      onPositionChanged: (seconds) =>
          widget.onVideoPositionChanged(videoUrl, seconds),
    );
  }

  Widget _buildTable(BuildContext context, dom.Element table) {
    final rows = table.querySelectorAll('tr');
    if (rows.isEmpty) {
      return const SizedBox.shrink();
    }
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(16),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Table(
          defaultColumnWidth: const IntrinsicColumnWidth(),
          children: rows
              .map(
                (row) => TableRow(
                  decoration: BoxDecoration(
                    color: row.querySelector('th') != null
                        ? Theme.of(context).colorScheme.surfaceContainerHighest
                        : null,
                  ),
                  children: row.children
                      .where((cell) =>
                          cell.localName == 'td' || cell.localName == 'th')
                      .map(
                        (cell) => Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 10),
                          child: Text.rich(
                            TextSpan(
                              style: (cell.localName == 'th'
                                      ? Theme.of(context).textTheme.titleSmall
                                      : Theme.of(context).textTheme.bodyMedium)
                                  ?.copyWith(
                                fontWeight: cell.localName == 'th'
                                    ? FontWeight.w700
                                    : null,
                              ),
                              children: _buildInlineSpans(context, cell.nodes),
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}
