import 'package:flutter/material.dart';

import '../api.dart';
import '../widgets.dart';

class NutrientsScreen extends StatefulWidget {
  const NutrientsScreen({super.key});

  @override
  State<NutrientsScreen> createState() => _NutrientsScreenState();
}

class _NutrientsScreenState extends State<NutrientsScreen> {
  final day = dateOnly(DateTime.now());
  Map<String, dynamic>? plan;
  List<dynamic> suggestions = [];
  String? error;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final p = await Api.getDay(day);
      final s = await Api.suggestions(day);
      if (mounted) {
        setState(() {
          plan = p;
          suggestions = s;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    if (error != null) return ErrorView(message: error!, onRetry: load);
    if (plan == null) return const Center(child: CircularProgressIndicator());

    final nutrients = plan!['nutrients'] as List;
    final kcal = nutrients.firstWhere((n) => n['key'] == 'kcal');
    final left = ((kcal['target'] as num) - (kcal['consumed'] as num)).round();

    return RefreshIndicator(
      onRefresh: load,
      child: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Daily Nutrition', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              const Text('CALORIES REMAINING'),
              Text('${left < 0 ? 0 : left} kcal',
                  style: const TextStyle(fontSize: 34, fontWeight: FontWeight.bold, color: Colors.green)),
              Text('${(kcal['consumed'] as num).round()} eaten / ${(kcal['target'] as num).round()} goal'),
            ]),
          ),
        ),
        const SizedBox(height: 8),
        for (final n in nutrients) _bar(n as Map<String, dynamic>),
        const Text('Dark = eaten so far · Light = after following today\'s plan',
            style: TextStyle(fontSize: 12, color: Colors.grey)),
        if (suggestions.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text('Quick Suggest', style: Theme.of(context).textTheme.titleLarge),
          for (final s in suggestions)
            ListTile(
              dense: true,
              leading: const Icon(Icons.add_circle_outline),
              title: Text('${s['name']} (1 ${s['unit']})'),
              subtitle: Text('${s['for']}: +${s['amount']} ${s['nutrient_unit']}'),
            ),
        ],
      ]),
    );
  }

  Widget _bar(Map<String, dynamic> n) {
    final target = (n['target'] as num).toDouble();
    final eaten = target == 0 ? 0.0 : ((n['consumed'] as num) / target).clamp(0.0, 1.0).toDouble();
    final expected = target == 0 ? 0.0 : ((n['expected'] as num) / target).clamp(0.0, 1.0).toDouble();
    final color = Theme.of(context).colorScheme.primary;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text(n['label'], style: const TextStyle(fontWeight: FontWeight.w600)),
          const Spacer(),
          Text('${(n['consumed'] as num).round()} / ${target.round()} ${n['unit']}'),
        ]),
        const SizedBox(height: 4),
        Stack(children: [
          LinearProgressIndicator(value: expected, minHeight: 10, color: color.withAlpha(77)),
          LinearProgressIndicator(
              value: eaten, minHeight: 10, color: color, backgroundColor: Colors.transparent),
        ]),
      ]),
    );
  }
}
