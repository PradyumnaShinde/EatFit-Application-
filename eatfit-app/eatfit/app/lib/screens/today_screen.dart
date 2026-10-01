import 'package:flutter/material.dart';

import '../api.dart';
import '../widgets.dart';

class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key});

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  DateTime day = dateOnly(DateTime.now());
  Map<String, dynamic>? data;
  String? error;
  bool busy = false;
  final Map<String, Set<int>> ticked = {}; // meal -> indexes of ticked items

  @override
  void initState() {
    super.initState();
    load();
  }

  /// Runs an API call that returns a fresh day plan, then redraws.
  Future<void> run(Future<Map<String, dynamic>> Function() call) async {
    setState(() => busy = true);
    try {
      final d = await call();
      if (!mounted) return;
      setState(() {
        data = d;
        error = null;
        ticked.clear();
      });
    } catch (e) {
      if (!mounted) return;
      if (data == null) {
        setState(() => error = e.toString());
      } else {
        toast(context, e.toString());
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> load() => run(() => Api.getDay(day));

  void _shiftDay(int days) {
    setState(() {
      day = day.add(Duration(days: days));
      data = null;
    });
    load();
  }

  String get _dayTitle {
    final today = dateOnly(DateTime.now());
    final diff = day.difference(today).inDays;
    if (diff == 0) return 'Today';
    if (diff == -1) return 'Yesterday';
    if (diff == 1) return 'Tomorrow';
    return isoDate(day);
  }

  @override
  Widget build(BuildContext context) {
    final header = Row(children: [
      IconButton(onPressed: busy ? null : () => _shiftDay(-1), icon: const Icon(Icons.chevron_left)),
      Expanded(
        child: Text("$_dayTitle's Diet",
            textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
      ),
      IconButton(onPressed: busy ? null : () => _shiftDay(1), icon: const Icon(Icons.chevron_right)),
    ]);

    if (error != null) {
      return Column(children: [header, Expanded(child: ErrorView(message: error!, onRetry: load))]);
    }
    if (data == null) return Column(children: [header, const Expanded(child: Center(child: CircularProgressIndicator()))]);

    final meals = data!['meals'] as List;
    final tips = data!['tips'] as List;

    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: busy ? null : _addOtherFood,
        icon: const Icon(Icons.add),
        label: const Text('Add food'),
      ),
      body: RefreshIndicator(
        onRefresh: load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 96),
          children: [
            header,
            if (busy) const LinearProgressIndicator(),
            for (final m in meals) _mealCard(m as Map<String, dynamic>),
            for (final t in tips)
              Card(
                color: Colors.orange.shade50,
                child: ListTile(leading: const Icon(Icons.lightbulb_outline), title: Text(t['text'])),
              ),
            const SizedBox(height: 12),
            const Text(disclaimer, style: TextStyle(fontSize: 11, color: Colors.grey)),
          ],
        ),
      ),
    );
  }

  Widget _mealCard(Map<String, dynamic> m) {
    final meal = m['meal'] as String;
    final status = m['status'] as String;
    final items = m['items'] as List;
    final picked = ticked.putIfAbsent(meal, () => <int>{});
    final planned = status == 'planned';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(capitalize(meal), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const Spacer(),
            Chip(label: Text(status)),
          ]),
          if (planned && m['menu_missing'] == true)
            const Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: Text('No menu for this meal yet. Add one in the Menu tab.'),
            ),
          if (status == 'skipped')
            Text(m['compensate'] == true ? 'Skipped, made up in later meals.' : 'Skipped.'),
          for (var i = 0; i < items.length; i++)
            planned
                ? CheckboxListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    value: picked.contains(i),
                    onChanged: (v) {
                      setState(() {
                        if (v == true) {
                          picked.add(i);
                        } else {
                          picked.remove(i);
                        }
                      });
                    },
                    title: Text(itemLabel(items[i])),
                    subtitle: items[i]['booster'] == true ? const Text('add-on') : null,
                  )
                : ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.check, color: Colors.green),
                    title: Text(itemLabel(items[i])),
                  ),
          const SizedBox(height: 4),
          if (planned)
            Row(children: [
              FilledButton(
                onPressed: busy ? null : () => _ate(meal, items, picked),
                child: const Text('I ate this'),
              ),
              const SizedBox(width: 8),
              OutlinedButton(onPressed: busy ? null : () => _skip(meal), child: const Text('Skip')),
            ])
          else
            TextButton(
              onPressed: busy ? null : () => run(() => Api.resetMeal(day, meal)),
              child: const Text('Undo'),
            ),
        ]),
      ),
    );
  }

  void _ate(String meal, List items, Set<int> picked) {
    if (picked.isEmpty) {
      toast(context, 'Tick the items you ate first');
      return;
    }
    final eaten = [
      for (final i in picked) {'food_id': items[i]['food_id'], 'servings': items[i]['servings']}
    ];
    run(() => Api.eat(day, meal, eaten));
  }

  Future<void> _skip(String meal) async {
    final compensate = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Skipping ${capitalize(meal)}'),
        content: const Text('Will you make up for it in your next meals?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('No')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Yes')),
        ],
      ),
    );
    if (compensate == null) return;
    run(() => Api.skip(day, meal, compensate));
  }

  /// Log something that wasn't in the plan.
  Future<void> _addOtherFood() async {
    final meals = (data!['meals'] as List).map((m) => m['meal'] as String).toList();
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => AddFoodDialog(meals: meals),
    );
    if (result == null) return;
    run(() => Api.eat(day, result['meal'], [
          {'food_id': result['food_id'], 'servings': result['servings']}
        ]));
  }
}

class AddFoodDialog extends StatefulWidget {
  final List<String> meals;
  const AddFoodDialog({super.key, required this.meals});

  @override
  State<AddFoodDialog> createState() => _AddFoodDialogState();
}

class _AddFoodDialogState extends State<AddFoodDialog> {
  late String meal = widget.meals.first;
  List<dynamic> results = [];
  Map<String, dynamic>? chosen;
  double servings = 1;

  Future<void> _search(String q) async {
    if (q.trim().length < 2) return;
    try {
      final r = await Api.searchFoods(q);
      if (mounted) setState(() => results = r);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add food'),
      content: SizedBox(
        width: 340,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButton<String>(
            value: meal,
            isExpanded: true,
            items: [for (final m in widget.meals) DropdownMenuItem(value: m, child: Text(capitalize(m)))],
            onChanged: (v) => setState(() => meal = v!),
          ),
          TextField(
            autofocus: true,
            decoration: const InputDecoration(hintText: 'Search e.g. paneer, banana'),
            onChanged: _search,
          ),
          SizedBox(
            height: 200,
            child: ListView(children: [
              for (final f in results)
                ListTile(
                  dense: true,
                  selected: chosen?['id'] == f['id'],
                  title: Text(f['name']),
                  subtitle: Text('1 ${f['unit']} = ${(f['nutrients']['kcal'] as num).round()} kcal'),
                  onTap: () => setState(() {
                    chosen = f;
                    servings = 1;
                  }),
                ),
            ]),
          ),
          if (chosen != null)
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              IconButton(
                onPressed: servings > 0.5 ? () => setState(() => servings -= 0.5) : null,
                icon: const Icon(Icons.remove_circle_outline),
              ),
              Text('$servings ${chosen!['unit']}'),
              IconButton(
                onPressed: servings < 10 ? () => setState(() => servings += 0.5) : null,
                icon: const Icon(Icons.add_circle_outline),
              ),
            ]),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: chosen == null
              ? null
              : () => Navigator.pop(context, {'meal': meal, 'food_id': chosen!['id'], 'servings': servings}),
          child: const Text('Add'),
        ),
      ],
    );
  }
}
