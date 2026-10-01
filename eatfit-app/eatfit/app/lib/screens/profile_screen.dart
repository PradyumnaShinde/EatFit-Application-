import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../api.dart';
import '../widgets.dart';

/// Used twice: as first-time onboarding (onboarding: true) and as the Profile tab.
class ProfileScreen extends StatefulWidget {
  final bool onboarding;
  final VoidCallback? onSaved;
  const ProfileScreen({super.key, this.onboarding = false, this.onSaved});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final name = TextEditingController();
  final age = TextEditingController();
  final height = TextEditingController();
  final weight = TextEditingController();
  final maxRotis = TextEditingController();
  String sex = 'male';
  String activity = 'light';
  String goal = 'maintain';
  String diet = 'veg';
  Set<String> allergens = {};
  Set<String> meals = {'breakfast', 'lunch', 'dinner'};
  bool boosters = true;
  bool agreed = false;
  bool busy = false;
  Map<String, dynamic>? targets;

  static const allMeals = ['breakfast', 'brunch', 'lunch', 'snacks', 'dinner', 'milk'];
  static const allAllergens = ['gluten', 'dairy', 'peanut', 'egg', 'fish'];
  static const activities = {
    'sedentary': 'Sedentary (mostly sitting)',
    'light': 'Light (walking around)',
    'moderate': 'Moderate (sport 3-5 days/week)',
    'active': 'Active (hard exercise most days)',
  };

  @override
  void initState() {
    super.initState();
    if (!widget.onboarding) _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.getMe();
      if (r == null || !mounted) return;
      final p = r['profile'];
      setState(() {
        name.text = p['name'] ?? '';
        age.text = '${p['age']}';
        height.text = '${(p['height_cm'] as num).round()}';
        weight.text = '${(p['weight_kg'] as num).round()}';
        sex = p['sex'];
        activity = p['activity'];
        goal = p['goal'];
        diet = p['diet'];
        allergens = Set<String>.from(p['allergens']);
        meals = Set<String>.from(p['meals']);
        boosters = p['allow_boosters'];
        final cap = p['capacity'] as Map<String, dynamic>;
        maxRotis.text = cap['roti'] == null ? '' : '${(cap['roti'] as num).toInt()}';
        targets = r['targets'];
      });
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
  }

  Future<void> _save() async {
    final a = int.tryParse(age.text);
    final h = double.tryParse(height.text);
    final w = double.tryParse(weight.text);
    if (a == null || h == null || w == null) {
      toast(context, 'Please fill in age, height and weight');
      return;
    }
    if (a < 18) {
      toast(context, 'EatFit is for adults (18+) for now');
      return;
    }
    if (meals.isEmpty) {
      toast(context, 'Pick at least one meal');
      return;
    }
    if (widget.onboarding && !agreed) {
      toast(context, 'Please accept the note at the bottom');
      return;
    }
    final rotis = int.tryParse(maxRotis.text);
    setState(() => busy = true);
    try {
      final r = await Api.saveMe({
        'name': name.text.trim(),
        'age': a,
        'sex': sex,
        'height_cm': h,
        'weight_kg': w,
        'activity': activity,
        'goal': goal,
        'diet': diet,
        'allergens': allergens.toList(),
        'meals': meals.toList(),
        'capacity': rotis == null ? <String, int>{} : {'roti': rotis},
        'allow_boosters': boosters,
      });
      if (!mounted) return;
      setState(() => targets = r['targets']);
      toast(context, 'Saved');
      widget.onSaved?.call();
    } catch (e) {
      if (mounted) toast(context, e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _deleteAccount() async {
    final sure = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete account?'),
        content: const Text('This permanently deletes your profile, menus, food logs and login. '
            'It cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (sure != true) return;
    try {
      await Api.deleteMe();
      await Supabase.instance.client.auth.signOut();
    } catch (e) {
      if (mounted) toast(context, e.toString());
    }
  }

  Widget _dropdown(String label, String value, Map<String, String> options, void Function(String) onPick) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: DropdownButtonFormField<String>(
        value: value,
        isExpanded: true,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        items: [
          for (final e in options.entries) DropdownMenuItem(value: e.key, child: Text(e.value))
        ],
        onChanged: (v) => setState(() => onPick(v!)),
      ),
    );
  }

  Widget _number(String label, TextEditingController c) => Padding(
        padding: const EdgeInsets.only(top: 12),
        child: TextField(
          controller: c,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(16), children: [
      Text(widget.onboarding ? 'Welcome! Tell us about you' : 'Profile',
          style: Theme.of(context).textTheme.headlineSmall),
      if (widget.onboarding)
        const Padding(
          padding: EdgeInsets.only(top: 4),
          child: Text('We use this to work out how much of each nutrient you need every day.'),
        ),
      Padding(
        padding: const EdgeInsets.only(top: 12),
        child: TextField(
          controller: name,
          decoration: const InputDecoration(labelText: 'Name', border: OutlineInputBorder()),
        ),
      ),
      _number('Age', age),
      _number('Height (cm)', height),
      _number('Weight (kg)', weight),
      _dropdown('Sex', sex, const {'male': 'Male', 'female': 'Female'}, (v) => sex = v),
      _dropdown('Activity', activity, activities, (v) => activity = v),
      _dropdown('Goal', goal, const {'lose': 'Lose weight', 'maintain': 'Stay the same', 'gain': 'Gain weight'},
          (v) => goal = v),
      _dropdown('Diet', diet, const {'veg': 'Vegetarian', 'egg': 'Eggetarian', 'nonveg': 'Non-vegetarian'},
          (v) => diet = v),
      const SizedBox(height: 16),
      const Text('Allergies'),
      Wrap(spacing: 6, children: [
        for (final a in allAllergens)
          FilterChip(
            label: Text(a),
            selected: allergens.contains(a),
            onSelected: (on) => setState(() => on ? allergens.add(a) : allergens.remove(a)),
          ),
      ]),
      const SizedBox(height: 12),
      const Text('Meals you usually have'),
      Wrap(spacing: 6, children: [
        for (final m in allMeals)
          FilterChip(
            label: Text(m),
            selected: meals.contains(m),
            onSelected: (on) => setState(() => on ? meals.add(m) : meals.remove(m)),
          ),
      ]),
      _number('Most rotis you can eat in a day (optional)', maxRotis),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Suggest add-ons (fruit, sprouts, curd...)'),
        value: boosters,
        onChanged: (v) => setState(() => boosters = v),
      ),
      if (widget.onboarding)
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          value: agreed,
          onChanged: (v) => setState(() => agreed = v ?? false),
          title: const Text(disclaimer, style: TextStyle(fontSize: 12)),
        ),
      const SizedBox(height: 8),
      FilledButton(
        onPressed: busy ? null : _save,
        child: Text(widget.onboarding ? 'Continue' : 'Save'),
      ),
      if (targets != null) ...[
        const SizedBox(height: 16),
        Text('Your daily targets', style: Theme.of(context).textTheme.titleMedium),
        Text('${targets!['kcal']} kcal · Protein ${targets!['protein']} g · '
            'Carbs ${targets!['carbs']} g · Fat ${targets!['fat']} g\n'
            'Fibre ${targets!['fibre']} g · Iron ${targets!['iron']} mg · '
            'Calcium ${targets!['calcium']} mg · Vitamin C ${targets!['vitc']} mg'),
      ],
      if (!widget.onboarding) ...[
        const Divider(height: 40),
        OutlinedButton.icon(
          onPressed: () => Supabase.instance.client.auth.signOut(),
          icon: const Icon(Icons.logout),
          label: const Text('Sign out'),
        ),
        TextButton(
          onPressed: _deleteAccount,
          child: const Text('Delete my account', style: TextStyle(color: Colors.red)),
        ),
        const Text(disclaimer, style: TextStyle(fontSize: 11, color: Colors.grey)),
      ],
    ]);
  }
}
