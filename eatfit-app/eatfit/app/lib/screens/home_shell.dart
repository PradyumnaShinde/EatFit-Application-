import 'package:flutter/material.dart';

import 'menu_screen.dart';
import 'nutrients_screen.dart';
import 'profile_screen.dart';
import 'today_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int index = 0;

  @override
  Widget build(BuildContext context) {
    // Pages are rebuilt on every tab switch, so they always show fresh data.
    final pages = <Widget>[
      const TodayScreen(),
      const NutrientsScreen(),
      const MenuScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      body: SafeArea(child: pages[index]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => setState(() => index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.restaurant_menu), label: 'Today'),
          NavigationDestination(icon: Icon(Icons.bar_chart), label: 'Nutrients'),
          NavigationDestination(icon: Icon(Icons.camera_alt_outlined), label: 'Menu'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }
}
