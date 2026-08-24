class UnitModel {
  final int id;
  final String name;
  final String code;
  final String address;
  final String city;
  final String state;
  final String status;
  final int? manager;
  final String? managerName;
  final int employeeCount;

  const UnitModel({
    required this.id,
    required this.name,
    this.code = '',
    this.address = '',
    this.city = '',
    this.state = '',
    this.status = 'active',
    this.manager,
    this.managerName,
    this.employeeCount = 0,
  });

  bool get isActive => status == 'active';

  /// Cidade e UF juntas, sem sobrar traço quando faltar uma das duas.
  String get location {
    if (city.isEmpty && state.isEmpty) return '';
    if (state.isEmpty) return city;
    if (city.isEmpty) return state;
    return '$city/$state';
  }

  factory UnitModel.fromJson(Map<String, dynamic> json) {
    return UnitModel(
      id: json['id'],
      name: json['name'] ?? '',
      code: json['code'] ?? '',
      address: json['address'] ?? '',
      city: json['city'] ?? '',
      state: json['state'] ?? '',
      status: json['status'] ?? 'active',
      manager: json['manager'],
      managerName: json['manager_name'],
      employeeCount: json['employee_count'] ?? 0,
    );
  }
}
