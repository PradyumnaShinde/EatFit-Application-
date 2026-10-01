import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../api.dart';
import '../widgets.dart';

class MenuScreen extends StatefulWidget {
  const MenuScreen({super.key});

  @override
  State<MenuScreen> createState() => _MenuScreenState();
}

class _MenuScreenState extends State<MenuScreen> {
  List<String> meals = ['breakfast', 'lunch', 'dinner'];
  final Map<String, TextEditingController> fields = {};
  Map<String, List<dynamic>> unmatched = {}; // meal -> [{input, suggestions}]
  int days = 1;
  bool busy = false;
  String status = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  TextEditingController _field(String meal) => fields.putIfAbsent(meal, () => TextEditingController());

  Future<void> _load() async {
    try {
      final me = await Api.getMe();
      final menu = await Api.getMenu(dateOnly(DateTime.now()));
      if (!mounted) return;
      setState(() {
        if (me != null) meals = List<String>.from(me['profile']['meals']);
        menu.forEach((meal, items) {
          _field(meal).text = [for (final i in items) i['name']].join(', ');
        });
      });
    } catch (e) {
      if (mounted) setState(() => status = e.toString());
    }
  }

  List<String> _names(String meal) =>
      _field(meal).text.split(',').map((s) => s.trim()).where((s) => s.isNotEmpty).toList();

  Future<void> _scan(ImageSource source) async {
    final photo = await ImagePicker().pickImage(source: source, maxWidth: 1600, imageQuality: 85);
    if (photo == null) return;
    setState(() {
      busy = true;
      status = 'Reading the menu...';
    });
    try {
      final r = await Api.scanMenu(photo.path);
      final found = r['meals'] as Map<String, dynamic>;
      setState(() {
        found.forEach((meal, v) {
          final names = [
            for (final m in v['matched']) m['name'] as String,
            for (final u in v['unmatched']) u['input'] as String,
          ].join(', ');
          if (meal == 'all') {
            for (final m in meals) {
              _field(m).text = names; // menu wasn't split by meal
            }
          } else if (meals.contains(meal)) {
            _field(meal).text = names;
          }
        });
        status = 'Check the items, fix anything wrong, then tap Save.';
      });
    } catch (e) {
      setState(() => status = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _save() async {
    final today = dateOnly(DateTime.now());
    setState(() => busy = true);
    try {
      final r = await Api.saveMenu(
          today, today.add(Duration(days: days - 1)), {for (final m in meals) m: _names(m)});
      final report = r['meals'] as Map<String, dynamic>;
      setState(() {
        unmatched = {
          for (final e in report.entries)
            if ((e.value['unmatched'] as List).isNotEmpty) e.key: e.value['unmatched'] as List
        };
        status = unmatched.isEmpty
            ? 'Saved! Your plan is ready in the Today tab.'
            : 'Saved. A few items need your help:';
      });
    } catch (e) {
      setState(() => status = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  /// Replace a name the user typed with the one they picked, then re-save.
  void _replace(String meal, String input, String replacement) {
    final names = _names(meal).map((n) => n == input ? replacement : n).toList();
    _field(meal).text = names.join(', ');
    _save();
  }

  Future<void> _addAsOwnFood(String meal, String input) async {
    final created = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => CustomFoodDialog(initialName: input),
    );
    if (created != null) _replace(meal, input, created['name']);
  }

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text('Menu', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(
          child: FilledButton.icon(
            onPressed: busy ? null : () => _scan(ImageSource.camera),
            icon: const Icon(Icons.camera_alt),
            label: const Text('Snap menu'),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: OutlinedButton.icon(
            onPressed: busy ? null : () => _scan(ImageSource.gallery),
            icon: const Icon(Icons.photo),
            label: const Text('From gallery'),
          ),
        ),
      ]),
      const SizedBox(height: 12),
      const Text('Or type what\'s being served, separated by commas:'),
      for (final m in meals)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: TextField(
            controller: _field(m),
            decoration: InputDecoration(
              labelText: capitalize(m),
              hintText: 'roti, dal, rice, curd',
              border: const OutlineInputBorder(),
            ),
          ),
        ),
      const SizedBox(height: 8),
      Row(children: [
        const Text('Same menu for'),
        const SizedBox(width: 8),
        DropdownButton<int>(
          value: days,
          items: const [
            DropdownMenuItem(value: 1, child: Text('today only')),
            DropdownMenuItem(value: 7, child: Text('7 days')),
            DropdownMenuItem(value: 30, child: Text('30 days')),
          ],
          onChanged: (v) => setState(() => days = v!),
        ),
      ]),
      FilledButton(onPressed: busy ? null : _save, child: const Text('Save menu')),
      if (busy) const LinearProgressIndicator(),
      const SizedBox(height: 12),
      Text(status),
      for (final e in unmatched.entries)
        for (final u in e.value)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${capitalize(e.key)}: we don\'t know "${u['input']}" yet. Did you mean:'),
                Wrap(spacing: 6, children: [
                  for (final s in u['suggestions'])
                    ActionChip(
                      label: Text(s['name']),
                      onPressed: busy ? null : () => _replace(e.key, u['input'], s['name']),
                    ),
                  ActionChip(
                    avatar: const Icon(Icons.add, size: 16),
                    label: const Text('Add as my own food'),
                    onPressed: busy ? null : () => _addAsOwnFood(e.key, u['input']),
                  ),
                ]),
              ]),
            ),
          ),
    ]);
  }
}

/// Lets a user add a dish we don't have (e.g. a hostel special). Values from the food packet
/// or a nutrition site are fine; they only affect this user.
class CustomFoodDialog extends StatefulWidget {
  final String initialName;
  const CustomFoodDialog({super.key, this.initialName = ''});

  @override
  State<CustomFoodDialog> createState() => _CustomFoodDialogState();
}

class _CustomFoodDialogState extends State<CustomFoodDialog> {
  late final name = TextEditingController(text: widget.initialName);
  final kcal = TextEditingController();
  final protein = TextEditingController();
  final carbs = TextEditingController();
  final fat = TextEditingController();
  final fibre = TextEditingController();
  String unit = 'bowl';
  String diet = 'veg';
  bool busy = false;

  double _num(TextEditingController c) => double.tryParse(c.text.trim()) ?? 0;

  Future<void> _save() async {
    if (name.text.trim().length < 2 || _num(kcal) <= 0) {
      toast(context, 'Give it a name and its calories');
      return;
    }
    setState(() => busy = true);
    try {
      final food = await Api.addFood({
        'name': name.text.trim(),
        'unit': unit,
        'step': unit == 'piece' ? 1 : 0.5,
        'diet': diet,
        'kcal': _num(kcal),
        'protein': _num(protein),
        'carbs': _num(carbs),
        'fat': _num(fat),
        'fibre': _num(fibre),
      });
      if (mounted) Navigator.pop(context, food);
    } catch (e) {
      if (mounted) toast(context, e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget _numField(String label, TextEditingController c) => TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label),
      );

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add your own food'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Name')),
          Row(children: [
            const Text('Per 1 '),
            DropdownButton<String>(
              value: unit,
              items: [
                for (final u in ['bowl', 'plate', 'piece', 'glass', 'cup'])
                  DropdownMenuItem(value: u, child: Text(u))
              ],
              onChanged: (v) => setState(() => unit = v!),
            ),
            const Spacer(),
            DropdownButton<String>(
              value: diet,
              items: const [
                DropdownMenuItem(value: 'veg', child: Text('Veg')),
                DropdownMenuItem(value: 'egg', child: Text('Egg')),
                DropdownMenuItem(value: 'nonveg', child: Text('Non-veg')),
              ],
              onChanged: (v) => setState(() => diet = v!),
            ),
          ]),
          _numField('Calories (kcal)', kcal),
          _numField('Protein (g)', protein),
          _numField('Carbs (g)', carbs),
          _numField('Fat (g)', fat),
          _numField('Fibre (g)', fibre),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(onPressed: busy ? null : _save, child: const Text('Save')),
      ],
    );
  }
}
