import 'package:flutter/material.dart';

class LessonMediaFrame extends StatelessWidget {
  const LessonMediaFrame({
    super.key,
    required this.child,
    this.minHeight = 220,
    this.maxHeight = 320,
    this.borderRadius = 18,
    this.backgroundColor = Colors.black,
  });

  final Widget child;
  final double minHeight;
  final double maxHeight;
  final double borderRadius;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final viewportWidth =
            constraints.maxWidth.isFinite && constraints.maxWidth > 0
                ? constraints.maxWidth
                : MediaQuery.sizeOf(context).width;
        final clampedHeight =
            (viewportWidth * 9 / 16).clamp(minHeight, maxHeight);
        return ClipRRect(
          borderRadius: BorderRadius.circular(borderRadius),
          child: SizedBox(
            width: double.infinity,
            height: clampedHeight,
            child: ColoredBox(
              color: backgroundColor,
              child: child,
            ),
          ),
        );
      },
    );
  }
}
