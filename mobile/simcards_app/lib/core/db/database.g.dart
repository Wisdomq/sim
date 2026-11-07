// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $LocalSimCardsTable extends LocalSimCards
    with TableInfo<$LocalSimCardsTable, LocalSimCard> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalSimCardsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _dealerIdMeta = const VerificationMeta(
    'dealerId',
  );
  @override
  late final GeneratedColumn<int> dealerId = GeneratedColumn<int>(
    'dealer_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _serialNumberMeta = const VerificationMeta(
    'serialNumber',
  );
  @override
  late final GeneratedColumn<String> serialNumber = GeneratedColumn<String>(
    'serial_number',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _currentBranchIdMeta = const VerificationMeta(
    'currentBranchId',
  );
  @override
  late final GeneratedColumn<int> currentBranchId = GeneratedColumn<int>(
    'current_branch_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _currentBaIdMeta = const VerificationMeta(
    'currentBaId',
  );
  @override
  late final GeneratedColumn<int> currentBaId = GeneratedColumn<int>(
    'current_ba_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _expiryDateMeta = const VerificationMeta(
    'expiryDate',
  );
  @override
  late final GeneratedColumn<String> expiryDate = GeneratedColumn<String>(
    'expiry_date',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    dealerId,
    serialNumber,
    status,
    currentBranchId,
    currentBaId,
    expiryDate,
    updatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_sim_cards';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalSimCard> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('dealer_id')) {
      context.handle(
        _dealerIdMeta,
        dealerId.isAcceptableOrUnknown(data['dealer_id']!, _dealerIdMeta),
      );
    } else if (isInserting) {
      context.missing(_dealerIdMeta);
    }
    if (data.containsKey('serial_number')) {
      context.handle(
        _serialNumberMeta,
        serialNumber.isAcceptableOrUnknown(
          data['serial_number']!,
          _serialNumberMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_serialNumberMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('current_branch_id')) {
      context.handle(
        _currentBranchIdMeta,
        currentBranchId.isAcceptableOrUnknown(
          data['current_branch_id']!,
          _currentBranchIdMeta,
        ),
      );
    }
    if (data.containsKey('current_ba_id')) {
      context.handle(
        _currentBaIdMeta,
        currentBaId.isAcceptableOrUnknown(
          data['current_ba_id']!,
          _currentBaIdMeta,
        ),
      );
    }
    if (data.containsKey('expiry_date')) {
      context.handle(
        _expiryDateMeta,
        expiryDate.isAcceptableOrUnknown(data['expiry_date']!, _expiryDateMeta),
      );
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    } else if (isInserting) {
      context.missing(_updatedAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalSimCard map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalSimCard(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      dealerId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}dealer_id'],
      )!,
      serialNumber: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}serial_number'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      currentBranchId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}current_branch_id'],
      ),
      currentBaId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}current_ba_id'],
      ),
      expiryDate: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}expiry_date'],
      ),
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $LocalSimCardsTable createAlias(String alias) {
    return $LocalSimCardsTable(attachedDatabase, alias);
  }
}

class LocalSimCard extends DataClass implements Insertable<LocalSimCard> {
  final int id;
  final int dealerId;
  final String serialNumber;
  final String status;
  final int? currentBranchId;
  final int? currentBaId;
  final String? expiryDate;
  final String updatedAt;
  const LocalSimCard({
    required this.id,
    required this.dealerId,
    required this.serialNumber,
    required this.status,
    this.currentBranchId,
    this.currentBaId,
    this.expiryDate,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['dealer_id'] = Variable<int>(dealerId);
    map['serial_number'] = Variable<String>(serialNumber);
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || currentBranchId != null) {
      map['current_branch_id'] = Variable<int>(currentBranchId);
    }
    if (!nullToAbsent || currentBaId != null) {
      map['current_ba_id'] = Variable<int>(currentBaId);
    }
    if (!nullToAbsent || expiryDate != null) {
      map['expiry_date'] = Variable<String>(expiryDate);
    }
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  LocalSimCardsCompanion toCompanion(bool nullToAbsent) {
    return LocalSimCardsCompanion(
      id: Value(id),
      dealerId: Value(dealerId),
      serialNumber: Value(serialNumber),
      status: Value(status),
      currentBranchId: currentBranchId == null && nullToAbsent
          ? const Value.absent()
          : Value(currentBranchId),
      currentBaId: currentBaId == null && nullToAbsent
          ? const Value.absent()
          : Value(currentBaId),
      expiryDate: expiryDate == null && nullToAbsent
          ? const Value.absent()
          : Value(expiryDate),
      updatedAt: Value(updatedAt),
    );
  }

  factory LocalSimCard.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalSimCard(
      id: serializer.fromJson<int>(json['id']),
      dealerId: serializer.fromJson<int>(json['dealerId']),
      serialNumber: serializer.fromJson<String>(json['serialNumber']),
      status: serializer.fromJson<String>(json['status']),
      currentBranchId: serializer.fromJson<int?>(json['currentBranchId']),
      currentBaId: serializer.fromJson<int?>(json['currentBaId']),
      expiryDate: serializer.fromJson<String?>(json['expiryDate']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'dealerId': serializer.toJson<int>(dealerId),
      'serialNumber': serializer.toJson<String>(serialNumber),
      'status': serializer.toJson<String>(status),
      'currentBranchId': serializer.toJson<int?>(currentBranchId),
      'currentBaId': serializer.toJson<int?>(currentBaId),
      'expiryDate': serializer.toJson<String?>(expiryDate),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  LocalSimCard copyWith({
    int? id,
    int? dealerId,
    String? serialNumber,
    String? status,
    Value<int?> currentBranchId = const Value.absent(),
    Value<int?> currentBaId = const Value.absent(),
    Value<String?> expiryDate = const Value.absent(),
    String? updatedAt,
  }) => LocalSimCard(
    id: id ?? this.id,
    dealerId: dealerId ?? this.dealerId,
    serialNumber: serialNumber ?? this.serialNumber,
    status: status ?? this.status,
    currentBranchId: currentBranchId.present
        ? currentBranchId.value
        : this.currentBranchId,
    currentBaId: currentBaId.present ? currentBaId.value : this.currentBaId,
    expiryDate: expiryDate.present ? expiryDate.value : this.expiryDate,
    updatedAt: updatedAt ?? this.updatedAt,
  );
  LocalSimCard copyWithCompanion(LocalSimCardsCompanion data) {
    return LocalSimCard(
      id: data.id.present ? data.id.value : this.id,
      dealerId: data.dealerId.present ? data.dealerId.value : this.dealerId,
      serialNumber: data.serialNumber.present
          ? data.serialNumber.value
          : this.serialNumber,
      status: data.status.present ? data.status.value : this.status,
      currentBranchId: data.currentBranchId.present
          ? data.currentBranchId.value
          : this.currentBranchId,
      currentBaId: data.currentBaId.present
          ? data.currentBaId.value
          : this.currentBaId,
      expiryDate: data.expiryDate.present
          ? data.expiryDate.value
          : this.expiryDate,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalSimCard(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('status: $status, ')
          ..write('currentBranchId: $currentBranchId, ')
          ..write('currentBaId: $currentBaId, ')
          ..write('expiryDate: $expiryDate, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    dealerId,
    serialNumber,
    status,
    currentBranchId,
    currentBaId,
    expiryDate,
    updatedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalSimCard &&
          other.id == this.id &&
          other.dealerId == this.dealerId &&
          other.serialNumber == this.serialNumber &&
          other.status == this.status &&
          other.currentBranchId == this.currentBranchId &&
          other.currentBaId == this.currentBaId &&
          other.expiryDate == this.expiryDate &&
          other.updatedAt == this.updatedAt);
}

class LocalSimCardsCompanion extends UpdateCompanion<LocalSimCard> {
  final Value<int> id;
  final Value<int> dealerId;
  final Value<String> serialNumber;
  final Value<String> status;
  final Value<int?> currentBranchId;
  final Value<int?> currentBaId;
  final Value<String?> expiryDate;
  final Value<String> updatedAt;
  const LocalSimCardsCompanion({
    this.id = const Value.absent(),
    this.dealerId = const Value.absent(),
    this.serialNumber = const Value.absent(),
    this.status = const Value.absent(),
    this.currentBranchId = const Value.absent(),
    this.currentBaId = const Value.absent(),
    this.expiryDate = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  LocalSimCardsCompanion.insert({
    this.id = const Value.absent(),
    required int dealerId,
    required String serialNumber,
    required String status,
    this.currentBranchId = const Value.absent(),
    this.currentBaId = const Value.absent(),
    this.expiryDate = const Value.absent(),
    required String updatedAt,
  }) : dealerId = Value(dealerId),
       serialNumber = Value(serialNumber),
       status = Value(status),
       updatedAt = Value(updatedAt);
  static Insertable<LocalSimCard> custom({
    Expression<int>? id,
    Expression<int>? dealerId,
    Expression<String>? serialNumber,
    Expression<String>? status,
    Expression<int>? currentBranchId,
    Expression<int>? currentBaId,
    Expression<String>? expiryDate,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (dealerId != null) 'dealer_id': dealerId,
      if (serialNumber != null) 'serial_number': serialNumber,
      if (status != null) 'status': status,
      if (currentBranchId != null) 'current_branch_id': currentBranchId,
      if (currentBaId != null) 'current_ba_id': currentBaId,
      if (expiryDate != null) 'expiry_date': expiryDate,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  LocalSimCardsCompanion copyWith({
    Value<int>? id,
    Value<int>? dealerId,
    Value<String>? serialNumber,
    Value<String>? status,
    Value<int?>? currentBranchId,
    Value<int?>? currentBaId,
    Value<String?>? expiryDate,
    Value<String>? updatedAt,
  }) {
    return LocalSimCardsCompanion(
      id: id ?? this.id,
      dealerId: dealerId ?? this.dealerId,
      serialNumber: serialNumber ?? this.serialNumber,
      status: status ?? this.status,
      currentBranchId: currentBranchId ?? this.currentBranchId,
      currentBaId: currentBaId ?? this.currentBaId,
      expiryDate: expiryDate ?? this.expiryDate,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (dealerId.present) {
      map['dealer_id'] = Variable<int>(dealerId.value);
    }
    if (serialNumber.present) {
      map['serial_number'] = Variable<String>(serialNumber.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (currentBranchId.present) {
      map['current_branch_id'] = Variable<int>(currentBranchId.value);
    }
    if (currentBaId.present) {
      map['current_ba_id'] = Variable<int>(currentBaId.value);
    }
    if (expiryDate.present) {
      map['expiry_date'] = Variable<String>(expiryDate.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalSimCardsCompanion(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('status: $status, ')
          ..write('currentBranchId: $currentBranchId, ')
          ..write('currentBaId: $currentBaId, ')
          ..write('expiryDate: $expiryDate, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $LocalSaleEventsTable extends LocalSaleEvents
    with TableInfo<$LocalSaleEventsTable, LocalSaleEvent> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalSaleEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _clientEventUuidMeta = const VerificationMeta(
    'clientEventUuid',
  );
  @override
  late final GeneratedColumn<String> clientEventUuid = GeneratedColumn<String>(
    'client_event_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'),
  );
  static const VerificationMeta _simCardIdMeta = const VerificationMeta(
    'simCardId',
  );
  @override
  late final GeneratedColumn<int> simCardId = GeneratedColumn<int>(
    'sim_card_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _serialNumberMeta = const VerificationMeta(
    'serialNumber',
  );
  @override
  late final GeneratedColumn<String> serialNumber = GeneratedColumn<String>(
    'serial_number',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _soldAtMeta = const VerificationMeta('soldAt');
  @override
  late final GeneratedColumn<String> soldAt = GeneratedColumn<String>(
    'sold_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _pendingSyncMeta = const VerificationMeta(
    'pendingSync',
  );
  @override
  late final GeneratedColumn<bool> pendingSync = GeneratedColumn<bool>(
    'pending_sync',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("pending_sync" IN (0, 1))',
    ),
    defaultValue: const Constant(true),
  );
  static const VerificationMeta _hasConflictMeta = const VerificationMeta(
    'hasConflict',
  );
  @override
  late final GeneratedColumn<bool> hasConflict = GeneratedColumn<bool>(
    'has_conflict',
    aliasedName,
    false,
    type: DriftSqlType.bool,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'CHECK ("has_conflict" IN (0, 1))',
    ),
    defaultValue: const Constant(false),
  );
  static const VerificationMeta _conflictReasonMeta = const VerificationMeta(
    'conflictReason',
  );
  @override
  late final GeneratedColumn<String> conflictReason = GeneratedColumn<String>(
    'conflict_reason',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    clientEventUuid,
    simCardId,
    serialNumber,
    soldAt,
    pendingSync,
    hasConflict,
    conflictReason,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_sale_events';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalSaleEvent> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('client_event_uuid')) {
      context.handle(
        _clientEventUuidMeta,
        clientEventUuid.isAcceptableOrUnknown(
          data['client_event_uuid']!,
          _clientEventUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_clientEventUuidMeta);
    }
    if (data.containsKey('sim_card_id')) {
      context.handle(
        _simCardIdMeta,
        simCardId.isAcceptableOrUnknown(data['sim_card_id']!, _simCardIdMeta),
      );
    } else if (isInserting) {
      context.missing(_simCardIdMeta);
    }
    if (data.containsKey('serial_number')) {
      context.handle(
        _serialNumberMeta,
        serialNumber.isAcceptableOrUnknown(
          data['serial_number']!,
          _serialNumberMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_serialNumberMeta);
    }
    if (data.containsKey('sold_at')) {
      context.handle(
        _soldAtMeta,
        soldAt.isAcceptableOrUnknown(data['sold_at']!, _soldAtMeta),
      );
    } else if (isInserting) {
      context.missing(_soldAtMeta);
    }
    if (data.containsKey('pending_sync')) {
      context.handle(
        _pendingSyncMeta,
        pendingSync.isAcceptableOrUnknown(
          data['pending_sync']!,
          _pendingSyncMeta,
        ),
      );
    }
    if (data.containsKey('has_conflict')) {
      context.handle(
        _hasConflictMeta,
        hasConflict.isAcceptableOrUnknown(
          data['has_conflict']!,
          _hasConflictMeta,
        ),
      );
    }
    if (data.containsKey('conflict_reason')) {
      context.handle(
        _conflictReasonMeta,
        conflictReason.isAcceptableOrUnknown(
          data['conflict_reason']!,
          _conflictReasonMeta,
        ),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalSaleEvent map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalSaleEvent(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      clientEventUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}client_event_uuid'],
      )!,
      simCardId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sim_card_id'],
      )!,
      serialNumber: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}serial_number'],
      )!,
      soldAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}sold_at'],
      )!,
      pendingSync: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}pending_sync'],
      )!,
      hasConflict: attachedDatabase.typeMapping.read(
        DriftSqlType.bool,
        data['${effectivePrefix}has_conflict'],
      )!,
      conflictReason: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}conflict_reason'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $LocalSaleEventsTable createAlias(String alias) {
    return $LocalSaleEventsTable(attachedDatabase, alias);
  }
}

class LocalSaleEvent extends DataClass implements Insertable<LocalSaleEvent> {
  final int id;
  final String clientEventUuid;
  final int simCardId;
  final String serialNumber;
  final String soldAt;
  final bool pendingSync;
  final bool hasConflict;
  final String? conflictReason;
  final String createdAt;
  const LocalSaleEvent({
    required this.id,
    required this.clientEventUuid,
    required this.simCardId,
    required this.serialNumber,
    required this.soldAt,
    required this.pendingSync,
    required this.hasConflict,
    this.conflictReason,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['client_event_uuid'] = Variable<String>(clientEventUuid);
    map['sim_card_id'] = Variable<int>(simCardId);
    map['serial_number'] = Variable<String>(serialNumber);
    map['sold_at'] = Variable<String>(soldAt);
    map['pending_sync'] = Variable<bool>(pendingSync);
    map['has_conflict'] = Variable<bool>(hasConflict);
    if (!nullToAbsent || conflictReason != null) {
      map['conflict_reason'] = Variable<String>(conflictReason);
    }
    map['created_at'] = Variable<String>(createdAt);
    return map;
  }

  LocalSaleEventsCompanion toCompanion(bool nullToAbsent) {
    return LocalSaleEventsCompanion(
      id: Value(id),
      clientEventUuid: Value(clientEventUuid),
      simCardId: Value(simCardId),
      serialNumber: Value(serialNumber),
      soldAt: Value(soldAt),
      pendingSync: Value(pendingSync),
      hasConflict: Value(hasConflict),
      conflictReason: conflictReason == null && nullToAbsent
          ? const Value.absent()
          : Value(conflictReason),
      createdAt: Value(createdAt),
    );
  }

  factory LocalSaleEvent.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalSaleEvent(
      id: serializer.fromJson<int>(json['id']),
      clientEventUuid: serializer.fromJson<String>(json['clientEventUuid']),
      simCardId: serializer.fromJson<int>(json['simCardId']),
      serialNumber: serializer.fromJson<String>(json['serialNumber']),
      soldAt: serializer.fromJson<String>(json['soldAt']),
      pendingSync: serializer.fromJson<bool>(json['pendingSync']),
      hasConflict: serializer.fromJson<bool>(json['hasConflict']),
      conflictReason: serializer.fromJson<String?>(json['conflictReason']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'clientEventUuid': serializer.toJson<String>(clientEventUuid),
      'simCardId': serializer.toJson<int>(simCardId),
      'serialNumber': serializer.toJson<String>(serialNumber),
      'soldAt': serializer.toJson<String>(soldAt),
      'pendingSync': serializer.toJson<bool>(pendingSync),
      'hasConflict': serializer.toJson<bool>(hasConflict),
      'conflictReason': serializer.toJson<String?>(conflictReason),
      'createdAt': serializer.toJson<String>(createdAt),
    };
  }

  LocalSaleEvent copyWith({
    int? id,
    String? clientEventUuid,
    int? simCardId,
    String? serialNumber,
    String? soldAt,
    bool? pendingSync,
    bool? hasConflict,
    Value<String?> conflictReason = const Value.absent(),
    String? createdAt,
  }) => LocalSaleEvent(
    id: id ?? this.id,
    clientEventUuid: clientEventUuid ?? this.clientEventUuid,
    simCardId: simCardId ?? this.simCardId,
    serialNumber: serialNumber ?? this.serialNumber,
    soldAt: soldAt ?? this.soldAt,
    pendingSync: pendingSync ?? this.pendingSync,
    hasConflict: hasConflict ?? this.hasConflict,
    conflictReason: conflictReason.present
        ? conflictReason.value
        : this.conflictReason,
    createdAt: createdAt ?? this.createdAt,
  );
  LocalSaleEvent copyWithCompanion(LocalSaleEventsCompanion data) {
    return LocalSaleEvent(
      id: data.id.present ? data.id.value : this.id,
      clientEventUuid: data.clientEventUuid.present
          ? data.clientEventUuid.value
          : this.clientEventUuid,
      simCardId: data.simCardId.present ? data.simCardId.value : this.simCardId,
      serialNumber: data.serialNumber.present
          ? data.serialNumber.value
          : this.serialNumber,
      soldAt: data.soldAt.present ? data.soldAt.value : this.soldAt,
      pendingSync: data.pendingSync.present
          ? data.pendingSync.value
          : this.pendingSync,
      hasConflict: data.hasConflict.present
          ? data.hasConflict.value
          : this.hasConflict,
      conflictReason: data.conflictReason.present
          ? data.conflictReason.value
          : this.conflictReason,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalSaleEvent(')
          ..write('id: $id, ')
          ..write('clientEventUuid: $clientEventUuid, ')
          ..write('simCardId: $simCardId, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('soldAt: $soldAt, ')
          ..write('pendingSync: $pendingSync, ')
          ..write('hasConflict: $hasConflict, ')
          ..write('conflictReason: $conflictReason, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    clientEventUuid,
    simCardId,
    serialNumber,
    soldAt,
    pendingSync,
    hasConflict,
    conflictReason,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalSaleEvent &&
          other.id == this.id &&
          other.clientEventUuid == this.clientEventUuid &&
          other.simCardId == this.simCardId &&
          other.serialNumber == this.serialNumber &&
          other.soldAt == this.soldAt &&
          other.pendingSync == this.pendingSync &&
          other.hasConflict == this.hasConflict &&
          other.conflictReason == this.conflictReason &&
          other.createdAt == this.createdAt);
}

class LocalSaleEventsCompanion extends UpdateCompanion<LocalSaleEvent> {
  final Value<int> id;
  final Value<String> clientEventUuid;
  final Value<int> simCardId;
  final Value<String> serialNumber;
  final Value<String> soldAt;
  final Value<bool> pendingSync;
  final Value<bool> hasConflict;
  final Value<String?> conflictReason;
  final Value<String> createdAt;
  const LocalSaleEventsCompanion({
    this.id = const Value.absent(),
    this.clientEventUuid = const Value.absent(),
    this.simCardId = const Value.absent(),
    this.serialNumber = const Value.absent(),
    this.soldAt = const Value.absent(),
    this.pendingSync = const Value.absent(),
    this.hasConflict = const Value.absent(),
    this.conflictReason = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  LocalSaleEventsCompanion.insert({
    this.id = const Value.absent(),
    required String clientEventUuid,
    required int simCardId,
    required String serialNumber,
    required String soldAt,
    this.pendingSync = const Value.absent(),
    this.hasConflict = const Value.absent(),
    this.conflictReason = const Value.absent(),
    required String createdAt,
  }) : clientEventUuid = Value(clientEventUuid),
       simCardId = Value(simCardId),
       serialNumber = Value(serialNumber),
       soldAt = Value(soldAt),
       createdAt = Value(createdAt);
  static Insertable<LocalSaleEvent> custom({
    Expression<int>? id,
    Expression<String>? clientEventUuid,
    Expression<int>? simCardId,
    Expression<String>? serialNumber,
    Expression<String>? soldAt,
    Expression<bool>? pendingSync,
    Expression<bool>? hasConflict,
    Expression<String>? conflictReason,
    Expression<String>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (clientEventUuid != null) 'client_event_uuid': clientEventUuid,
      if (simCardId != null) 'sim_card_id': simCardId,
      if (serialNumber != null) 'serial_number': serialNumber,
      if (soldAt != null) 'sold_at': soldAt,
      if (pendingSync != null) 'pending_sync': pendingSync,
      if (hasConflict != null) 'has_conflict': hasConflict,
      if (conflictReason != null) 'conflict_reason': conflictReason,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  LocalSaleEventsCompanion copyWith({
    Value<int>? id,
    Value<String>? clientEventUuid,
    Value<int>? simCardId,
    Value<String>? serialNumber,
    Value<String>? soldAt,
    Value<bool>? pendingSync,
    Value<bool>? hasConflict,
    Value<String?>? conflictReason,
    Value<String>? createdAt,
  }) {
    return LocalSaleEventsCompanion(
      id: id ?? this.id,
      clientEventUuid: clientEventUuid ?? this.clientEventUuid,
      simCardId: simCardId ?? this.simCardId,
      serialNumber: serialNumber ?? this.serialNumber,
      soldAt: soldAt ?? this.soldAt,
      pendingSync: pendingSync ?? this.pendingSync,
      hasConflict: hasConflict ?? this.hasConflict,
      conflictReason: conflictReason ?? this.conflictReason,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (clientEventUuid.present) {
      map['client_event_uuid'] = Variable<String>(clientEventUuid.value);
    }
    if (simCardId.present) {
      map['sim_card_id'] = Variable<int>(simCardId.value);
    }
    if (serialNumber.present) {
      map['serial_number'] = Variable<String>(serialNumber.value);
    }
    if (soldAt.present) {
      map['sold_at'] = Variable<String>(soldAt.value);
    }
    if (pendingSync.present) {
      map['pending_sync'] = Variable<bool>(pendingSync.value);
    }
    if (hasConflict.present) {
      map['has_conflict'] = Variable<bool>(hasConflict.value);
    }
    if (conflictReason.present) {
      map['conflict_reason'] = Variable<String>(conflictReason.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalSaleEventsCompanion(')
          ..write('id: $id, ')
          ..write('clientEventUuid: $clientEventUuid, ')
          ..write('simCardId: $simCardId, ')
          ..write('serialNumber: $serialNumber, ')
          ..write('soldAt: $soldAt, ')
          ..write('pendingSync: $pendingSync, ')
          ..write('hasConflict: $hasConflict, ')
          ..write('conflictReason: $conflictReason, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $LocalBrandAmbassadorsTable extends LocalBrandAmbassadors
    with TableInfo<$LocalBrandAmbassadorsTable, LocalBrandAmbassador> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalBrandAmbassadorsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _dealerIdMeta = const VerificationMeta(
    'dealerId',
  );
  @override
  late final GeneratedColumn<int> dealerId = GeneratedColumn<int>(
    'dealer_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _branchIdMeta = const VerificationMeta(
    'branchId',
  );
  @override
  late final GeneratedColumn<int> branchId = GeneratedColumn<int>(
    'branch_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _emailMeta = const VerificationMeta('email');
  @override
  late final GeneratedColumn<String> email = GeneratedColumn<String>(
    'email',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _soldCountMeta = const VerificationMeta(
    'soldCount',
  );
  @override
  late final GeneratedColumn<int> soldCount = GeneratedColumn<int>(
    'sold_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _unsoldCountMeta = const VerificationMeta(
    'unsoldCount',
  );
  @override
  late final GeneratedColumn<int> unsoldCount = GeneratedColumn<int>(
    'unsold_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant(''),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    dealerId,
    branchId,
    name,
    email,
    status,
    soldCount,
    unsoldCount,
    updatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_brand_ambassadors';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalBrandAmbassador> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('dealer_id')) {
      context.handle(
        _dealerIdMeta,
        dealerId.isAcceptableOrUnknown(data['dealer_id']!, _dealerIdMeta),
      );
    } else if (isInserting) {
      context.missing(_dealerIdMeta);
    }
    if (data.containsKey('branch_id')) {
      context.handle(
        _branchIdMeta,
        branchId.isAcceptableOrUnknown(data['branch_id']!, _branchIdMeta),
      );
    } else if (isInserting) {
      context.missing(_branchIdMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('email')) {
      context.handle(
        _emailMeta,
        email.isAcceptableOrUnknown(data['email']!, _emailMeta),
      );
    } else if (isInserting) {
      context.missing(_emailMeta);
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('sold_count')) {
      context.handle(
        _soldCountMeta,
        soldCount.isAcceptableOrUnknown(data['sold_count']!, _soldCountMeta),
      );
    }
    if (data.containsKey('unsold_count')) {
      context.handle(
        _unsoldCountMeta,
        unsoldCount.isAcceptableOrUnknown(
          data['unsold_count']!,
          _unsoldCountMeta,
        ),
      );
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalBrandAmbassador map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalBrandAmbassador(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      dealerId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}dealer_id'],
      )!,
      branchId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}branch_id'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      email: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}email'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      soldCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sold_count'],
      )!,
      unsoldCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}unsold_count'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $LocalBrandAmbassadorsTable createAlias(String alias) {
    return $LocalBrandAmbassadorsTable(attachedDatabase, alias);
  }
}

class LocalBrandAmbassador extends DataClass
    implements Insertable<LocalBrandAmbassador> {
  final int id;
  final int dealerId;
  final int branchId;
  final String name;
  final String email;
  final String status;
  final int soldCount;
  final int unsoldCount;
  final String updatedAt;
  const LocalBrandAmbassador({
    required this.id,
    required this.dealerId,
    required this.branchId,
    required this.name,
    required this.email,
    required this.status,
    required this.soldCount,
    required this.unsoldCount,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['dealer_id'] = Variable<int>(dealerId);
    map['branch_id'] = Variable<int>(branchId);
    map['name'] = Variable<String>(name);
    map['email'] = Variable<String>(email);
    map['status'] = Variable<String>(status);
    map['sold_count'] = Variable<int>(soldCount);
    map['unsold_count'] = Variable<int>(unsoldCount);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  LocalBrandAmbassadorsCompanion toCompanion(bool nullToAbsent) {
    return LocalBrandAmbassadorsCompanion(
      id: Value(id),
      dealerId: Value(dealerId),
      branchId: Value(branchId),
      name: Value(name),
      email: Value(email),
      status: Value(status),
      soldCount: Value(soldCount),
      unsoldCount: Value(unsoldCount),
      updatedAt: Value(updatedAt),
    );
  }

  factory LocalBrandAmbassador.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalBrandAmbassador(
      id: serializer.fromJson<int>(json['id']),
      dealerId: serializer.fromJson<int>(json['dealerId']),
      branchId: serializer.fromJson<int>(json['branchId']),
      name: serializer.fromJson<String>(json['name']),
      email: serializer.fromJson<String>(json['email']),
      status: serializer.fromJson<String>(json['status']),
      soldCount: serializer.fromJson<int>(json['soldCount']),
      unsoldCount: serializer.fromJson<int>(json['unsoldCount']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'dealerId': serializer.toJson<int>(dealerId),
      'branchId': serializer.toJson<int>(branchId),
      'name': serializer.toJson<String>(name),
      'email': serializer.toJson<String>(email),
      'status': serializer.toJson<String>(status),
      'soldCount': serializer.toJson<int>(soldCount),
      'unsoldCount': serializer.toJson<int>(unsoldCount),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  LocalBrandAmbassador copyWith({
    int? id,
    int? dealerId,
    int? branchId,
    String? name,
    String? email,
    String? status,
    int? soldCount,
    int? unsoldCount,
    String? updatedAt,
  }) => LocalBrandAmbassador(
    id: id ?? this.id,
    dealerId: dealerId ?? this.dealerId,
    branchId: branchId ?? this.branchId,
    name: name ?? this.name,
    email: email ?? this.email,
    status: status ?? this.status,
    soldCount: soldCount ?? this.soldCount,
    unsoldCount: unsoldCount ?? this.unsoldCount,
    updatedAt: updatedAt ?? this.updatedAt,
  );
  LocalBrandAmbassador copyWithCompanion(LocalBrandAmbassadorsCompanion data) {
    return LocalBrandAmbassador(
      id: data.id.present ? data.id.value : this.id,
      dealerId: data.dealerId.present ? data.dealerId.value : this.dealerId,
      branchId: data.branchId.present ? data.branchId.value : this.branchId,
      name: data.name.present ? data.name.value : this.name,
      email: data.email.present ? data.email.value : this.email,
      status: data.status.present ? data.status.value : this.status,
      soldCount: data.soldCount.present ? data.soldCount.value : this.soldCount,
      unsoldCount: data.unsoldCount.present
          ? data.unsoldCount.value
          : this.unsoldCount,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalBrandAmbassador(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('branchId: $branchId, ')
          ..write('name: $name, ')
          ..write('email: $email, ')
          ..write('status: $status, ')
          ..write('soldCount: $soldCount, ')
          ..write('unsoldCount: $unsoldCount, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    dealerId,
    branchId,
    name,
    email,
    status,
    soldCount,
    unsoldCount,
    updatedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalBrandAmbassador &&
          other.id == this.id &&
          other.dealerId == this.dealerId &&
          other.branchId == this.branchId &&
          other.name == this.name &&
          other.email == this.email &&
          other.status == this.status &&
          other.soldCount == this.soldCount &&
          other.unsoldCount == this.unsoldCount &&
          other.updatedAt == this.updatedAt);
}

class LocalBrandAmbassadorsCompanion
    extends UpdateCompanion<LocalBrandAmbassador> {
  final Value<int> id;
  final Value<int> dealerId;
  final Value<int> branchId;
  final Value<String> name;
  final Value<String> email;
  final Value<String> status;
  final Value<int> soldCount;
  final Value<int> unsoldCount;
  final Value<String> updatedAt;
  const LocalBrandAmbassadorsCompanion({
    this.id = const Value.absent(),
    this.dealerId = const Value.absent(),
    this.branchId = const Value.absent(),
    this.name = const Value.absent(),
    this.email = const Value.absent(),
    this.status = const Value.absent(),
    this.soldCount = const Value.absent(),
    this.unsoldCount = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  LocalBrandAmbassadorsCompanion.insert({
    this.id = const Value.absent(),
    required int dealerId,
    required int branchId,
    required String name,
    required String email,
    required String status,
    this.soldCount = const Value.absent(),
    this.unsoldCount = const Value.absent(),
    this.updatedAt = const Value.absent(),
  }) : dealerId = Value(dealerId),
       branchId = Value(branchId),
       name = Value(name),
       email = Value(email),
       status = Value(status);
  static Insertable<LocalBrandAmbassador> custom({
    Expression<int>? id,
    Expression<int>? dealerId,
    Expression<int>? branchId,
    Expression<String>? name,
    Expression<String>? email,
    Expression<String>? status,
    Expression<int>? soldCount,
    Expression<int>? unsoldCount,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (dealerId != null) 'dealer_id': dealerId,
      if (branchId != null) 'branch_id': branchId,
      if (name != null) 'name': name,
      if (email != null) 'email': email,
      if (status != null) 'status': status,
      if (soldCount != null) 'sold_count': soldCount,
      if (unsoldCount != null) 'unsold_count': unsoldCount,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  LocalBrandAmbassadorsCompanion copyWith({
    Value<int>? id,
    Value<int>? dealerId,
    Value<int>? branchId,
    Value<String>? name,
    Value<String>? email,
    Value<String>? status,
    Value<int>? soldCount,
    Value<int>? unsoldCount,
    Value<String>? updatedAt,
  }) {
    return LocalBrandAmbassadorsCompanion(
      id: id ?? this.id,
      dealerId: dealerId ?? this.dealerId,
      branchId: branchId ?? this.branchId,
      name: name ?? this.name,
      email: email ?? this.email,
      status: status ?? this.status,
      soldCount: soldCount ?? this.soldCount,
      unsoldCount: unsoldCount ?? this.unsoldCount,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (dealerId.present) {
      map['dealer_id'] = Variable<int>(dealerId.value);
    }
    if (branchId.present) {
      map['branch_id'] = Variable<int>(branchId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (email.present) {
      map['email'] = Variable<String>(email.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (soldCount.present) {
      map['sold_count'] = Variable<int>(soldCount.value);
    }
    if (unsoldCount.present) {
      map['unsold_count'] = Variable<int>(unsoldCount.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalBrandAmbassadorsCompanion(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('branchId: $branchId, ')
          ..write('name: $name, ')
          ..write('email: $email, ')
          ..write('status: $status, ')
          ..write('soldCount: $soldCount, ')
          ..write('unsoldCount: $unsoldCount, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $LocalBranchesTable extends LocalBranches
    with TableInfo<$LocalBranchesTable, LocalBranche> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalBranchesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _dealerIdMeta = const VerificationMeta(
    'dealerId',
  );
  @override
  late final GeneratedColumn<int> dealerId = GeneratedColumn<int>(
    'dealer_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _nameMeta = const VerificationMeta('name');
  @override
  late final GeneratedColumn<String> name = GeneratedColumn<String>(
    'name',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _typeMeta = const VerificationMeta('type');
  @override
  late final GeneratedColumn<String> type = GeneratedColumn<String>(
    'type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _idNumberMeta = const VerificationMeta(
    'idNumber',
  );
  @override
  late final GeneratedColumn<String> idNumber = GeneratedColumn<String>(
    'id_number',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _photoUrlMeta = const VerificationMeta(
    'photoUrl',
  );
  @override
  late final GeneratedColumn<String> photoUrl = GeneratedColumn<String>(
    'photo_url',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<String> updatedAt = GeneratedColumn<String>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant(''),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    dealerId,
    name,
    type,
    idNumber,
    photoUrl,
    createdAt,
    updatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_branches';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalBranche> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('dealer_id')) {
      context.handle(
        _dealerIdMeta,
        dealerId.isAcceptableOrUnknown(data['dealer_id']!, _dealerIdMeta),
      );
    } else if (isInserting) {
      context.missing(_dealerIdMeta);
    }
    if (data.containsKey('name')) {
      context.handle(
        _nameMeta,
        name.isAcceptableOrUnknown(data['name']!, _nameMeta),
      );
    } else if (isInserting) {
      context.missing(_nameMeta);
    }
    if (data.containsKey('type')) {
      context.handle(
        _typeMeta,
        type.isAcceptableOrUnknown(data['type']!, _typeMeta),
      );
    } else if (isInserting) {
      context.missing(_typeMeta);
    }
    if (data.containsKey('id_number')) {
      context.handle(
        _idNumberMeta,
        idNumber.isAcceptableOrUnknown(data['id_number']!, _idNumberMeta),
      );
    } else if (isInserting) {
      context.missing(_idNumberMeta);
    }
    if (data.containsKey('photo_url')) {
      context.handle(
        _photoUrlMeta,
        photoUrl.isAcceptableOrUnknown(data['photo_url']!, _photoUrlMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalBranche map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalBranche(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      dealerId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}dealer_id'],
      )!,
      name: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}name'],
      )!,
      type: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}type'],
      )!,
      idNumber: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}id_number'],
      )!,
      photoUrl: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}photo_url'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $LocalBranchesTable createAlias(String alias) {
    return $LocalBranchesTable(attachedDatabase, alias);
  }
}

class LocalBranche extends DataClass implements Insertable<LocalBranche> {
  final int id;
  final int dealerId;
  final String name;
  final String type;
  final String idNumber;
  final String? photoUrl;
  final String createdAt;
  final String updatedAt;
  const LocalBranche({
    required this.id,
    required this.dealerId,
    required this.name,
    required this.type,
    required this.idNumber,
    this.photoUrl,
    required this.createdAt,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['dealer_id'] = Variable<int>(dealerId);
    map['name'] = Variable<String>(name);
    map['type'] = Variable<String>(type);
    map['id_number'] = Variable<String>(idNumber);
    if (!nullToAbsent || photoUrl != null) {
      map['photo_url'] = Variable<String>(photoUrl);
    }
    map['created_at'] = Variable<String>(createdAt);
    map['updated_at'] = Variable<String>(updatedAt);
    return map;
  }

  LocalBranchesCompanion toCompanion(bool nullToAbsent) {
    return LocalBranchesCompanion(
      id: Value(id),
      dealerId: Value(dealerId),
      name: Value(name),
      type: Value(type),
      idNumber: Value(idNumber),
      photoUrl: photoUrl == null && nullToAbsent
          ? const Value.absent()
          : Value(photoUrl),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory LocalBranche.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalBranche(
      id: serializer.fromJson<int>(json['id']),
      dealerId: serializer.fromJson<int>(json['dealerId']),
      name: serializer.fromJson<String>(json['name']),
      type: serializer.fromJson<String>(json['type']),
      idNumber: serializer.fromJson<String>(json['idNumber']),
      photoUrl: serializer.fromJson<String?>(json['photoUrl']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      updatedAt: serializer.fromJson<String>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'dealerId': serializer.toJson<int>(dealerId),
      'name': serializer.toJson<String>(name),
      'type': serializer.toJson<String>(type),
      'idNumber': serializer.toJson<String>(idNumber),
      'photoUrl': serializer.toJson<String?>(photoUrl),
      'createdAt': serializer.toJson<String>(createdAt),
      'updatedAt': serializer.toJson<String>(updatedAt),
    };
  }

  LocalBranche copyWith({
    int? id,
    int? dealerId,
    String? name,
    String? type,
    String? idNumber,
    Value<String?> photoUrl = const Value.absent(),
    String? createdAt,
    String? updatedAt,
  }) => LocalBranche(
    id: id ?? this.id,
    dealerId: dealerId ?? this.dealerId,
    name: name ?? this.name,
    type: type ?? this.type,
    idNumber: idNumber ?? this.idNumber,
    photoUrl: photoUrl.present ? photoUrl.value : this.photoUrl,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
  );
  LocalBranche copyWithCompanion(LocalBranchesCompanion data) {
    return LocalBranche(
      id: data.id.present ? data.id.value : this.id,
      dealerId: data.dealerId.present ? data.dealerId.value : this.dealerId,
      name: data.name.present ? data.name.value : this.name,
      type: data.type.present ? data.type.value : this.type,
      idNumber: data.idNumber.present ? data.idNumber.value : this.idNumber,
      photoUrl: data.photoUrl.present ? data.photoUrl.value : this.photoUrl,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalBranche(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('name: $name, ')
          ..write('type: $type, ')
          ..write('idNumber: $idNumber, ')
          ..write('photoUrl: $photoUrl, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    dealerId,
    name,
    type,
    idNumber,
    photoUrl,
    createdAt,
    updatedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalBranche &&
          other.id == this.id &&
          other.dealerId == this.dealerId &&
          other.name == this.name &&
          other.type == this.type &&
          other.idNumber == this.idNumber &&
          other.photoUrl == this.photoUrl &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class LocalBranchesCompanion extends UpdateCompanion<LocalBranche> {
  final Value<int> id;
  final Value<int> dealerId;
  final Value<String> name;
  final Value<String> type;
  final Value<String> idNumber;
  final Value<String?> photoUrl;
  final Value<String> createdAt;
  final Value<String> updatedAt;
  const LocalBranchesCompanion({
    this.id = const Value.absent(),
    this.dealerId = const Value.absent(),
    this.name = const Value.absent(),
    this.type = const Value.absent(),
    this.idNumber = const Value.absent(),
    this.photoUrl = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  LocalBranchesCompanion.insert({
    this.id = const Value.absent(),
    required int dealerId,
    required String name,
    required String type,
    required String idNumber,
    this.photoUrl = const Value.absent(),
    required String createdAt,
    this.updatedAt = const Value.absent(),
  }) : dealerId = Value(dealerId),
       name = Value(name),
       type = Value(type),
       idNumber = Value(idNumber),
       createdAt = Value(createdAt);
  static Insertable<LocalBranche> custom({
    Expression<int>? id,
    Expression<int>? dealerId,
    Expression<String>? name,
    Expression<String>? type,
    Expression<String>? idNumber,
    Expression<String>? photoUrl,
    Expression<String>? createdAt,
    Expression<String>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (dealerId != null) 'dealer_id': dealerId,
      if (name != null) 'name': name,
      if (type != null) 'type': type,
      if (idNumber != null) 'id_number': idNumber,
      if (photoUrl != null) 'photo_url': photoUrl,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  LocalBranchesCompanion copyWith({
    Value<int>? id,
    Value<int>? dealerId,
    Value<String>? name,
    Value<String>? type,
    Value<String>? idNumber,
    Value<String?>? photoUrl,
    Value<String>? createdAt,
    Value<String>? updatedAt,
  }) {
    return LocalBranchesCompanion(
      id: id ?? this.id,
      dealerId: dealerId ?? this.dealerId,
      name: name ?? this.name,
      type: type ?? this.type,
      idNumber: idNumber ?? this.idNumber,
      photoUrl: photoUrl ?? this.photoUrl,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (dealerId.present) {
      map['dealer_id'] = Variable<int>(dealerId.value);
    }
    if (name.present) {
      map['name'] = Variable<String>(name.value);
    }
    if (type.present) {
      map['type'] = Variable<String>(type.value);
    }
    if (idNumber.present) {
      map['id_number'] = Variable<String>(idNumber.value);
    }
    if (photoUrl.present) {
      map['photo_url'] = Variable<String>(photoUrl.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<String>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalBranchesCompanion(')
          ..write('id: $id, ')
          ..write('dealerId: $dealerId, ')
          ..write('name: $name, ')
          ..write('type: $type, ')
          ..write('idNumber: $idNumber, ')
          ..write('photoUrl: $photoUrl, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $LocalPendingSyncItemsTable extends LocalPendingSyncItems
    with TableInfo<$LocalPendingSyncItemsTable, LocalPendingSyncItem> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $LocalPendingSyncItemsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _eventTypeMeta = const VerificationMeta(
    'eventType',
  );
  @override
  late final GeneratedColumn<String> eventType = GeneratedColumn<String>(
    'event_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _clientEventUuidMeta = const VerificationMeta(
    'clientEventUuid',
  );
  @override
  late final GeneratedColumn<String> clientEventUuid = GeneratedColumn<String>(
    'client_event_uuid',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'),
  );
  static const VerificationMeta _payloadMeta = const VerificationMeta(
    'payload',
  );
  @override
  late final GeneratedColumn<String> payload = GeneratedColumn<String>(
    'payload',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<String> createdAt = GeneratedColumn<String>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _retryCountMeta = const VerificationMeta(
    'retryCount',
  );
  @override
  late final GeneratedColumn<int> retryCount = GeneratedColumn<int>(
    'retry_count',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    eventType,
    clientEventUuid,
    payload,
    createdAt,
    retryCount,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'local_pending_sync_items';
  @override
  VerificationContext validateIntegrity(
    Insertable<LocalPendingSyncItem> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('event_type')) {
      context.handle(
        _eventTypeMeta,
        eventType.isAcceptableOrUnknown(data['event_type']!, _eventTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_eventTypeMeta);
    }
    if (data.containsKey('client_event_uuid')) {
      context.handle(
        _clientEventUuidMeta,
        clientEventUuid.isAcceptableOrUnknown(
          data['client_event_uuid']!,
          _clientEventUuidMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_clientEventUuidMeta);
    }
    if (data.containsKey('payload')) {
      context.handle(
        _payloadMeta,
        payload.isAcceptableOrUnknown(data['payload']!, _payloadMeta),
      );
    } else if (isInserting) {
      context.missing(_payloadMeta);
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    } else if (isInserting) {
      context.missing(_createdAtMeta);
    }
    if (data.containsKey('retry_count')) {
      context.handle(
        _retryCountMeta,
        retryCount.isAcceptableOrUnknown(data['retry_count']!, _retryCountMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  LocalPendingSyncItem map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return LocalPendingSyncItem(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      eventType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}event_type'],
      )!,
      clientEventUuid: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}client_event_uuid'],
      )!,
      payload: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}created_at'],
      )!,
      retryCount: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}retry_count'],
      )!,
    );
  }

  @override
  $LocalPendingSyncItemsTable createAlias(String alias) {
    return $LocalPendingSyncItemsTable(attachedDatabase, alias);
  }
}

class LocalPendingSyncItem extends DataClass
    implements Insertable<LocalPendingSyncItem> {
  final int id;
  final String eventType;
  final String clientEventUuid;
  final String payload;
  final String createdAt;
  final int retryCount;
  const LocalPendingSyncItem({
    required this.id,
    required this.eventType,
    required this.clientEventUuid,
    required this.payload,
    required this.createdAt,
    required this.retryCount,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['event_type'] = Variable<String>(eventType);
    map['client_event_uuid'] = Variable<String>(clientEventUuid);
    map['payload'] = Variable<String>(payload);
    map['created_at'] = Variable<String>(createdAt);
    map['retry_count'] = Variable<int>(retryCount);
    return map;
  }

  LocalPendingSyncItemsCompanion toCompanion(bool nullToAbsent) {
    return LocalPendingSyncItemsCompanion(
      id: Value(id),
      eventType: Value(eventType),
      clientEventUuid: Value(clientEventUuid),
      payload: Value(payload),
      createdAt: Value(createdAt),
      retryCount: Value(retryCount),
    );
  }

  factory LocalPendingSyncItem.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return LocalPendingSyncItem(
      id: serializer.fromJson<int>(json['id']),
      eventType: serializer.fromJson<String>(json['eventType']),
      clientEventUuid: serializer.fromJson<String>(json['clientEventUuid']),
      payload: serializer.fromJson<String>(json['payload']),
      createdAt: serializer.fromJson<String>(json['createdAt']),
      retryCount: serializer.fromJson<int>(json['retryCount']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'eventType': serializer.toJson<String>(eventType),
      'clientEventUuid': serializer.toJson<String>(clientEventUuid),
      'payload': serializer.toJson<String>(payload),
      'createdAt': serializer.toJson<String>(createdAt),
      'retryCount': serializer.toJson<int>(retryCount),
    };
  }

  LocalPendingSyncItem copyWith({
    int? id,
    String? eventType,
    String? clientEventUuid,
    String? payload,
    String? createdAt,
    int? retryCount,
  }) => LocalPendingSyncItem(
    id: id ?? this.id,
    eventType: eventType ?? this.eventType,
    clientEventUuid: clientEventUuid ?? this.clientEventUuid,
    payload: payload ?? this.payload,
    createdAt: createdAt ?? this.createdAt,
    retryCount: retryCount ?? this.retryCount,
  );
  LocalPendingSyncItem copyWithCompanion(LocalPendingSyncItemsCompanion data) {
    return LocalPendingSyncItem(
      id: data.id.present ? data.id.value : this.id,
      eventType: data.eventType.present ? data.eventType.value : this.eventType,
      clientEventUuid: data.clientEventUuid.present
          ? data.clientEventUuid.value
          : this.clientEventUuid,
      payload: data.payload.present ? data.payload.value : this.payload,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      retryCount: data.retryCount.present
          ? data.retryCount.value
          : this.retryCount,
    );
  }

  @override
  String toString() {
    return (StringBuffer('LocalPendingSyncItem(')
          ..write('id: $id, ')
          ..write('eventType: $eventType, ')
          ..write('clientEventUuid: $clientEventUuid, ')
          ..write('payload: $payload, ')
          ..write('createdAt: $createdAt, ')
          ..write('retryCount: $retryCount')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    eventType,
    clientEventUuid,
    payload,
    createdAt,
    retryCount,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is LocalPendingSyncItem &&
          other.id == this.id &&
          other.eventType == this.eventType &&
          other.clientEventUuid == this.clientEventUuid &&
          other.payload == this.payload &&
          other.createdAt == this.createdAt &&
          other.retryCount == this.retryCount);
}

class LocalPendingSyncItemsCompanion
    extends UpdateCompanion<LocalPendingSyncItem> {
  final Value<int> id;
  final Value<String> eventType;
  final Value<String> clientEventUuid;
  final Value<String> payload;
  final Value<String> createdAt;
  final Value<int> retryCount;
  const LocalPendingSyncItemsCompanion({
    this.id = const Value.absent(),
    this.eventType = const Value.absent(),
    this.clientEventUuid = const Value.absent(),
    this.payload = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.retryCount = const Value.absent(),
  });
  LocalPendingSyncItemsCompanion.insert({
    this.id = const Value.absent(),
    required String eventType,
    required String clientEventUuid,
    required String payload,
    required String createdAt,
    this.retryCount = const Value.absent(),
  }) : eventType = Value(eventType),
       clientEventUuid = Value(clientEventUuid),
       payload = Value(payload),
       createdAt = Value(createdAt);
  static Insertable<LocalPendingSyncItem> custom({
    Expression<int>? id,
    Expression<String>? eventType,
    Expression<String>? clientEventUuid,
    Expression<String>? payload,
    Expression<String>? createdAt,
    Expression<int>? retryCount,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (eventType != null) 'event_type': eventType,
      if (clientEventUuid != null) 'client_event_uuid': clientEventUuid,
      if (payload != null) 'payload': payload,
      if (createdAt != null) 'created_at': createdAt,
      if (retryCount != null) 'retry_count': retryCount,
    });
  }

  LocalPendingSyncItemsCompanion copyWith({
    Value<int>? id,
    Value<String>? eventType,
    Value<String>? clientEventUuid,
    Value<String>? payload,
    Value<String>? createdAt,
    Value<int>? retryCount,
  }) {
    return LocalPendingSyncItemsCompanion(
      id: id ?? this.id,
      eventType: eventType ?? this.eventType,
      clientEventUuid: clientEventUuid ?? this.clientEventUuid,
      payload: payload ?? this.payload,
      createdAt: createdAt ?? this.createdAt,
      retryCount: retryCount ?? this.retryCount,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (eventType.present) {
      map['event_type'] = Variable<String>(eventType.value);
    }
    if (clientEventUuid.present) {
      map['client_event_uuid'] = Variable<String>(clientEventUuid.value);
    }
    if (payload.present) {
      map['payload'] = Variable<String>(payload.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<String>(createdAt.value);
    }
    if (retryCount.present) {
      map['retry_count'] = Variable<int>(retryCount.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('LocalPendingSyncItemsCompanion(')
          ..write('id: $id, ')
          ..write('eventType: $eventType, ')
          ..write('clientEventUuid: $clientEventUuid, ')
          ..write('payload: $payload, ')
          ..write('createdAt: $createdAt, ')
          ..write('retryCount: $retryCount')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $LocalSimCardsTable localSimCards = $LocalSimCardsTable(this);
  late final $LocalSaleEventsTable localSaleEvents = $LocalSaleEventsTable(
    this,
  );
  late final $LocalBrandAmbassadorsTable localBrandAmbassadors =
      $LocalBrandAmbassadorsTable(this);
  late final $LocalBranchesTable localBranches = $LocalBranchesTable(this);
  late final $LocalPendingSyncItemsTable localPendingSyncItems =
      $LocalPendingSyncItemsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    localSimCards,
    localSaleEvents,
    localBrandAmbassadors,
    localBranches,
    localPendingSyncItems,
  ];
}

typedef $$LocalSimCardsTableCreateCompanionBuilder =
    LocalSimCardsCompanion Function({
      Value<int> id,
      required int dealerId,
      required String serialNumber,
      required String status,
      Value<int?> currentBranchId,
      Value<int?> currentBaId,
      Value<String?> expiryDate,
      required String updatedAt,
    });
typedef $$LocalSimCardsTableUpdateCompanionBuilder =
    LocalSimCardsCompanion Function({
      Value<int> id,
      Value<int> dealerId,
      Value<String> serialNumber,
      Value<String> status,
      Value<int?> currentBranchId,
      Value<int?> currentBaId,
      Value<String?> expiryDate,
      Value<String> updatedAt,
    });

class $$LocalSimCardsTableFilterComposer
    extends Composer<_$AppDatabase, $LocalSimCardsTable> {
  $$LocalSimCardsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get currentBranchId => $composableBuilder(
    column: $table.currentBranchId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get currentBaId => $composableBuilder(
    column: $table.currentBaId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get expiryDate => $composableBuilder(
    column: $table.expiryDate,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalSimCardsTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalSimCardsTable> {
  $$LocalSimCardsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get currentBranchId => $composableBuilder(
    column: $table.currentBranchId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get currentBaId => $composableBuilder(
    column: $table.currentBaId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get expiryDate => $composableBuilder(
    column: $table.expiryDate,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalSimCardsTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalSimCardsTable> {
  $$LocalSimCardsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get dealerId =>
      $composableBuilder(column: $table.dealerId, builder: (column) => column);

  GeneratedColumn<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => column,
  );

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<int> get currentBranchId => $composableBuilder(
    column: $table.currentBranchId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get currentBaId => $composableBuilder(
    column: $table.currentBaId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get expiryDate => $composableBuilder(
    column: $table.expiryDate,
    builder: (column) => column,
  );

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$LocalSimCardsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalSimCardsTable,
          LocalSimCard,
          $$LocalSimCardsTableFilterComposer,
          $$LocalSimCardsTableOrderingComposer,
          $$LocalSimCardsTableAnnotationComposer,
          $$LocalSimCardsTableCreateCompanionBuilder,
          $$LocalSimCardsTableUpdateCompanionBuilder,
          (
            LocalSimCard,
            BaseReferences<_$AppDatabase, $LocalSimCardsTable, LocalSimCard>,
          ),
          LocalSimCard,
          PrefetchHooks Function()
        > {
  $$LocalSimCardsTableTableManager(_$AppDatabase db, $LocalSimCardsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalSimCardsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LocalSimCardsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LocalSimCardsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> dealerId = const Value.absent(),
                Value<String> serialNumber = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<int?> currentBranchId = const Value.absent(),
                Value<int?> currentBaId = const Value.absent(),
                Value<String?> expiryDate = const Value.absent(),
                Value<String> updatedAt = const Value.absent(),
              }) => LocalSimCardsCompanion(
                id: id,
                dealerId: dealerId,
                serialNumber: serialNumber,
                status: status,
                currentBranchId: currentBranchId,
                currentBaId: currentBaId,
                expiryDate: expiryDate,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int dealerId,
                required String serialNumber,
                required String status,
                Value<int?> currentBranchId = const Value.absent(),
                Value<int?> currentBaId = const Value.absent(),
                Value<String?> expiryDate = const Value.absent(),
                required String updatedAt,
              }) => LocalSimCardsCompanion.insert(
                id: id,
                dealerId: dealerId,
                serialNumber: serialNumber,
                status: status,
                currentBranchId: currentBranchId,
                currentBaId: currentBaId,
                expiryDate: expiryDate,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalSimCardsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalSimCardsTable,
      LocalSimCard,
      $$LocalSimCardsTableFilterComposer,
      $$LocalSimCardsTableOrderingComposer,
      $$LocalSimCardsTableAnnotationComposer,
      $$LocalSimCardsTableCreateCompanionBuilder,
      $$LocalSimCardsTableUpdateCompanionBuilder,
      (
        LocalSimCard,
        BaseReferences<_$AppDatabase, $LocalSimCardsTable, LocalSimCard>,
      ),
      LocalSimCard,
      PrefetchHooks Function()
    >;
typedef $$LocalSaleEventsTableCreateCompanionBuilder =
    LocalSaleEventsCompanion Function({
      Value<int> id,
      required String clientEventUuid,
      required int simCardId,
      required String serialNumber,
      required String soldAt,
      Value<bool> pendingSync,
      Value<bool> hasConflict,
      Value<String?> conflictReason,
      required String createdAt,
    });
typedef $$LocalSaleEventsTableUpdateCompanionBuilder =
    LocalSaleEventsCompanion Function({
      Value<int> id,
      Value<String> clientEventUuid,
      Value<int> simCardId,
      Value<String> serialNumber,
      Value<String> soldAt,
      Value<bool> pendingSync,
      Value<bool> hasConflict,
      Value<String?> conflictReason,
      Value<String> createdAt,
    });

class $$LocalSaleEventsTableFilterComposer
    extends Composer<_$AppDatabase, $LocalSaleEventsTable> {
  $$LocalSaleEventsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get simCardId => $composableBuilder(
    column: $table.simCardId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get soldAt => $composableBuilder(
    column: $table.soldAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get pendingSync => $composableBuilder(
    column: $table.pendingSync,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<bool> get hasConflict => $composableBuilder(
    column: $table.hasConflict,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get conflictReason => $composableBuilder(
    column: $table.conflictReason,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalSaleEventsTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalSaleEventsTable> {
  $$LocalSaleEventsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get simCardId => $composableBuilder(
    column: $table.simCardId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get soldAt => $composableBuilder(
    column: $table.soldAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get pendingSync => $composableBuilder(
    column: $table.pendingSync,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<bool> get hasConflict => $composableBuilder(
    column: $table.hasConflict,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get conflictReason => $composableBuilder(
    column: $table.conflictReason,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalSaleEventsTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalSaleEventsTable> {
  $$LocalSaleEventsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => column,
  );

  GeneratedColumn<int> get simCardId =>
      $composableBuilder(column: $table.simCardId, builder: (column) => column);

  GeneratedColumn<String> get serialNumber => $composableBuilder(
    column: $table.serialNumber,
    builder: (column) => column,
  );

  GeneratedColumn<String> get soldAt =>
      $composableBuilder(column: $table.soldAt, builder: (column) => column);

  GeneratedColumn<bool> get pendingSync => $composableBuilder(
    column: $table.pendingSync,
    builder: (column) => column,
  );

  GeneratedColumn<bool> get hasConflict => $composableBuilder(
    column: $table.hasConflict,
    builder: (column) => column,
  );

  GeneratedColumn<String> get conflictReason => $composableBuilder(
    column: $table.conflictReason,
    builder: (column) => column,
  );

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$LocalSaleEventsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalSaleEventsTable,
          LocalSaleEvent,
          $$LocalSaleEventsTableFilterComposer,
          $$LocalSaleEventsTableOrderingComposer,
          $$LocalSaleEventsTableAnnotationComposer,
          $$LocalSaleEventsTableCreateCompanionBuilder,
          $$LocalSaleEventsTableUpdateCompanionBuilder,
          (
            LocalSaleEvent,
            BaseReferences<
              _$AppDatabase,
              $LocalSaleEventsTable,
              LocalSaleEvent
            >,
          ),
          LocalSaleEvent,
          PrefetchHooks Function()
        > {
  $$LocalSaleEventsTableTableManager(
    _$AppDatabase db,
    $LocalSaleEventsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalSaleEventsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LocalSaleEventsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LocalSaleEventsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> clientEventUuid = const Value.absent(),
                Value<int> simCardId = const Value.absent(),
                Value<String> serialNumber = const Value.absent(),
                Value<String> soldAt = const Value.absent(),
                Value<bool> pendingSync = const Value.absent(),
                Value<bool> hasConflict = const Value.absent(),
                Value<String?> conflictReason = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
              }) => LocalSaleEventsCompanion(
                id: id,
                clientEventUuid: clientEventUuid,
                simCardId: simCardId,
                serialNumber: serialNumber,
                soldAt: soldAt,
                pendingSync: pendingSync,
                hasConflict: hasConflict,
                conflictReason: conflictReason,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String clientEventUuid,
                required int simCardId,
                required String serialNumber,
                required String soldAt,
                Value<bool> pendingSync = const Value.absent(),
                Value<bool> hasConflict = const Value.absent(),
                Value<String?> conflictReason = const Value.absent(),
                required String createdAt,
              }) => LocalSaleEventsCompanion.insert(
                id: id,
                clientEventUuid: clientEventUuid,
                simCardId: simCardId,
                serialNumber: serialNumber,
                soldAt: soldAt,
                pendingSync: pendingSync,
                hasConflict: hasConflict,
                conflictReason: conflictReason,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalSaleEventsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalSaleEventsTable,
      LocalSaleEvent,
      $$LocalSaleEventsTableFilterComposer,
      $$LocalSaleEventsTableOrderingComposer,
      $$LocalSaleEventsTableAnnotationComposer,
      $$LocalSaleEventsTableCreateCompanionBuilder,
      $$LocalSaleEventsTableUpdateCompanionBuilder,
      (
        LocalSaleEvent,
        BaseReferences<_$AppDatabase, $LocalSaleEventsTable, LocalSaleEvent>,
      ),
      LocalSaleEvent,
      PrefetchHooks Function()
    >;
typedef $$LocalBrandAmbassadorsTableCreateCompanionBuilder =
    LocalBrandAmbassadorsCompanion Function({
      Value<int> id,
      required int dealerId,
      required int branchId,
      required String name,
      required String email,
      required String status,
      Value<int> soldCount,
      Value<int> unsoldCount,
      Value<String> updatedAt,
    });
typedef $$LocalBrandAmbassadorsTableUpdateCompanionBuilder =
    LocalBrandAmbassadorsCompanion Function({
      Value<int> id,
      Value<int> dealerId,
      Value<int> branchId,
      Value<String> name,
      Value<String> email,
      Value<String> status,
      Value<int> soldCount,
      Value<int> unsoldCount,
      Value<String> updatedAt,
    });

class $$LocalBrandAmbassadorsTableFilterComposer
    extends Composer<_$AppDatabase, $LocalBrandAmbassadorsTable> {
  $$LocalBrandAmbassadorsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get branchId => $composableBuilder(
    column: $table.branchId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get email => $composableBuilder(
    column: $table.email,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get soldCount => $composableBuilder(
    column: $table.soldCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get unsoldCount => $composableBuilder(
    column: $table.unsoldCount,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalBrandAmbassadorsTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalBrandAmbassadorsTable> {
  $$LocalBrandAmbassadorsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get branchId => $composableBuilder(
    column: $table.branchId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get email => $composableBuilder(
    column: $table.email,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get soldCount => $composableBuilder(
    column: $table.soldCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get unsoldCount => $composableBuilder(
    column: $table.unsoldCount,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalBrandAmbassadorsTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalBrandAmbassadorsTable> {
  $$LocalBrandAmbassadorsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get dealerId =>
      $composableBuilder(column: $table.dealerId, builder: (column) => column);

  GeneratedColumn<int> get branchId =>
      $composableBuilder(column: $table.branchId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get email =>
      $composableBuilder(column: $table.email, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<int> get soldCount =>
      $composableBuilder(column: $table.soldCount, builder: (column) => column);

  GeneratedColumn<int> get unsoldCount => $composableBuilder(
    column: $table.unsoldCount,
    builder: (column) => column,
  );

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$LocalBrandAmbassadorsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalBrandAmbassadorsTable,
          LocalBrandAmbassador,
          $$LocalBrandAmbassadorsTableFilterComposer,
          $$LocalBrandAmbassadorsTableOrderingComposer,
          $$LocalBrandAmbassadorsTableAnnotationComposer,
          $$LocalBrandAmbassadorsTableCreateCompanionBuilder,
          $$LocalBrandAmbassadorsTableUpdateCompanionBuilder,
          (
            LocalBrandAmbassador,
            BaseReferences<
              _$AppDatabase,
              $LocalBrandAmbassadorsTable,
              LocalBrandAmbassador
            >,
          ),
          LocalBrandAmbassador,
          PrefetchHooks Function()
        > {
  $$LocalBrandAmbassadorsTableTableManager(
    _$AppDatabase db,
    $LocalBrandAmbassadorsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalBrandAmbassadorsTableFilterComposer(
                $db: db,
                $table: table,
              ),
          createOrderingComposer: () =>
              $$LocalBrandAmbassadorsTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$LocalBrandAmbassadorsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> dealerId = const Value.absent(),
                Value<int> branchId = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<String> email = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<int> soldCount = const Value.absent(),
                Value<int> unsoldCount = const Value.absent(),
                Value<String> updatedAt = const Value.absent(),
              }) => LocalBrandAmbassadorsCompanion(
                id: id,
                dealerId: dealerId,
                branchId: branchId,
                name: name,
                email: email,
                status: status,
                soldCount: soldCount,
                unsoldCount: unsoldCount,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int dealerId,
                required int branchId,
                required String name,
                required String email,
                required String status,
                Value<int> soldCount = const Value.absent(),
                Value<int> unsoldCount = const Value.absent(),
                Value<String> updatedAt = const Value.absent(),
              }) => LocalBrandAmbassadorsCompanion.insert(
                id: id,
                dealerId: dealerId,
                branchId: branchId,
                name: name,
                email: email,
                status: status,
                soldCount: soldCount,
                unsoldCount: unsoldCount,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalBrandAmbassadorsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalBrandAmbassadorsTable,
      LocalBrandAmbassador,
      $$LocalBrandAmbassadorsTableFilterComposer,
      $$LocalBrandAmbassadorsTableOrderingComposer,
      $$LocalBrandAmbassadorsTableAnnotationComposer,
      $$LocalBrandAmbassadorsTableCreateCompanionBuilder,
      $$LocalBrandAmbassadorsTableUpdateCompanionBuilder,
      (
        LocalBrandAmbassador,
        BaseReferences<
          _$AppDatabase,
          $LocalBrandAmbassadorsTable,
          LocalBrandAmbassador
        >,
      ),
      LocalBrandAmbassador,
      PrefetchHooks Function()
    >;
typedef $$LocalBranchesTableCreateCompanionBuilder =
    LocalBranchesCompanion Function({
      Value<int> id,
      required int dealerId,
      required String name,
      required String type,
      required String idNumber,
      Value<String?> photoUrl,
      required String createdAt,
      Value<String> updatedAt,
    });
typedef $$LocalBranchesTableUpdateCompanionBuilder =
    LocalBranchesCompanion Function({
      Value<int> id,
      Value<int> dealerId,
      Value<String> name,
      Value<String> type,
      Value<String> idNumber,
      Value<String?> photoUrl,
      Value<String> createdAt,
      Value<String> updatedAt,
    });

class $$LocalBranchesTableFilterComposer
    extends Composer<_$AppDatabase, $LocalBranchesTable> {
  $$LocalBranchesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get type => $composableBuilder(
    column: $table.type,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get idNumber => $composableBuilder(
    column: $table.idNumber,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get photoUrl => $composableBuilder(
    column: $table.photoUrl,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalBranchesTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalBranchesTable> {
  $$LocalBranchesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get dealerId => $composableBuilder(
    column: $table.dealerId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get name => $composableBuilder(
    column: $table.name,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get type => $composableBuilder(
    column: $table.type,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get idNumber => $composableBuilder(
    column: $table.idNumber,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get photoUrl => $composableBuilder(
    column: $table.photoUrl,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalBranchesTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalBranchesTable> {
  $$LocalBranchesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get dealerId =>
      $composableBuilder(column: $table.dealerId, builder: (column) => column);

  GeneratedColumn<String> get name =>
      $composableBuilder(column: $table.name, builder: (column) => column);

  GeneratedColumn<String> get type =>
      $composableBuilder(column: $table.type, builder: (column) => column);

  GeneratedColumn<String> get idNumber =>
      $composableBuilder(column: $table.idNumber, builder: (column) => column);

  GeneratedColumn<String> get photoUrl =>
      $composableBuilder(column: $table.photoUrl, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<String> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$LocalBranchesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalBranchesTable,
          LocalBranche,
          $$LocalBranchesTableFilterComposer,
          $$LocalBranchesTableOrderingComposer,
          $$LocalBranchesTableAnnotationComposer,
          $$LocalBranchesTableCreateCompanionBuilder,
          $$LocalBranchesTableUpdateCompanionBuilder,
          (
            LocalBranche,
            BaseReferences<_$AppDatabase, $LocalBranchesTable, LocalBranche>,
          ),
          LocalBranche,
          PrefetchHooks Function()
        > {
  $$LocalBranchesTableTableManager(_$AppDatabase db, $LocalBranchesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalBranchesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$LocalBranchesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$LocalBranchesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> dealerId = const Value.absent(),
                Value<String> name = const Value.absent(),
                Value<String> type = const Value.absent(),
                Value<String> idNumber = const Value.absent(),
                Value<String?> photoUrl = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
                Value<String> updatedAt = const Value.absent(),
              }) => LocalBranchesCompanion(
                id: id,
                dealerId: dealerId,
                name: name,
                type: type,
                idNumber: idNumber,
                photoUrl: photoUrl,
                createdAt: createdAt,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int dealerId,
                required String name,
                required String type,
                required String idNumber,
                Value<String?> photoUrl = const Value.absent(),
                required String createdAt,
                Value<String> updatedAt = const Value.absent(),
              }) => LocalBranchesCompanion.insert(
                id: id,
                dealerId: dealerId,
                name: name,
                type: type,
                idNumber: idNumber,
                photoUrl: photoUrl,
                createdAt: createdAt,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalBranchesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalBranchesTable,
      LocalBranche,
      $$LocalBranchesTableFilterComposer,
      $$LocalBranchesTableOrderingComposer,
      $$LocalBranchesTableAnnotationComposer,
      $$LocalBranchesTableCreateCompanionBuilder,
      $$LocalBranchesTableUpdateCompanionBuilder,
      (
        LocalBranche,
        BaseReferences<_$AppDatabase, $LocalBranchesTable, LocalBranche>,
      ),
      LocalBranche,
      PrefetchHooks Function()
    >;
typedef $$LocalPendingSyncItemsTableCreateCompanionBuilder =
    LocalPendingSyncItemsCompanion Function({
      Value<int> id,
      required String eventType,
      required String clientEventUuid,
      required String payload,
      required String createdAt,
      Value<int> retryCount,
    });
typedef $$LocalPendingSyncItemsTableUpdateCompanionBuilder =
    LocalPendingSyncItemsCompanion Function({
      Value<int> id,
      Value<String> eventType,
      Value<String> clientEventUuid,
      Value<String> payload,
      Value<String> createdAt,
      Value<int> retryCount,
    });

class $$LocalPendingSyncItemsTableFilterComposer
    extends Composer<_$AppDatabase, $LocalPendingSyncItemsTable> {
  $$LocalPendingSyncItemsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get eventType => $composableBuilder(
    column: $table.eventType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnFilters(column),
  );
}

class $$LocalPendingSyncItemsTableOrderingComposer
    extends Composer<_$AppDatabase, $LocalPendingSyncItemsTable> {
  $$LocalPendingSyncItemsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get eventType => $composableBuilder(
    column: $table.eventType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payload => $composableBuilder(
    column: $table.payload,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$LocalPendingSyncItemsTableAnnotationComposer
    extends Composer<_$AppDatabase, $LocalPendingSyncItemsTable> {
  $$LocalPendingSyncItemsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get eventType =>
      $composableBuilder(column: $table.eventType, builder: (column) => column);

  GeneratedColumn<String> get clientEventUuid => $composableBuilder(
    column: $table.clientEventUuid,
    builder: (column) => column,
  );

  GeneratedColumn<String> get payload =>
      $composableBuilder(column: $table.payload, builder: (column) => column);

  GeneratedColumn<String> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<int> get retryCount => $composableBuilder(
    column: $table.retryCount,
    builder: (column) => column,
  );
}

class $$LocalPendingSyncItemsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $LocalPendingSyncItemsTable,
          LocalPendingSyncItem,
          $$LocalPendingSyncItemsTableFilterComposer,
          $$LocalPendingSyncItemsTableOrderingComposer,
          $$LocalPendingSyncItemsTableAnnotationComposer,
          $$LocalPendingSyncItemsTableCreateCompanionBuilder,
          $$LocalPendingSyncItemsTableUpdateCompanionBuilder,
          (
            LocalPendingSyncItem,
            BaseReferences<
              _$AppDatabase,
              $LocalPendingSyncItemsTable,
              LocalPendingSyncItem
            >,
          ),
          LocalPendingSyncItem,
          PrefetchHooks Function()
        > {
  $$LocalPendingSyncItemsTableTableManager(
    _$AppDatabase db,
    $LocalPendingSyncItemsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$LocalPendingSyncItemsTableFilterComposer(
                $db: db,
                $table: table,
              ),
          createOrderingComposer: () =>
              $$LocalPendingSyncItemsTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$LocalPendingSyncItemsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> eventType = const Value.absent(),
                Value<String> clientEventUuid = const Value.absent(),
                Value<String> payload = const Value.absent(),
                Value<String> createdAt = const Value.absent(),
                Value<int> retryCount = const Value.absent(),
              }) => LocalPendingSyncItemsCompanion(
                id: id,
                eventType: eventType,
                clientEventUuid: clientEventUuid,
                payload: payload,
                createdAt: createdAt,
                retryCount: retryCount,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String eventType,
                required String clientEventUuid,
                required String payload,
                required String createdAt,
                Value<int> retryCount = const Value.absent(),
              }) => LocalPendingSyncItemsCompanion.insert(
                id: id,
                eventType: eventType,
                clientEventUuid: clientEventUuid,
                payload: payload,
                createdAt: createdAt,
                retryCount: retryCount,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$LocalPendingSyncItemsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $LocalPendingSyncItemsTable,
      LocalPendingSyncItem,
      $$LocalPendingSyncItemsTableFilterComposer,
      $$LocalPendingSyncItemsTableOrderingComposer,
      $$LocalPendingSyncItemsTableAnnotationComposer,
      $$LocalPendingSyncItemsTableCreateCompanionBuilder,
      $$LocalPendingSyncItemsTableUpdateCompanionBuilder,
      (
        LocalPendingSyncItem,
        BaseReferences<
          _$AppDatabase,
          $LocalPendingSyncItemsTable,
          LocalPendingSyncItem
        >,
      ),
      LocalPendingSyncItem,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$LocalSimCardsTableTableManager get localSimCards =>
      $$LocalSimCardsTableTableManager(_db, _db.localSimCards);
  $$LocalSaleEventsTableTableManager get localSaleEvents =>
      $$LocalSaleEventsTableTableManager(_db, _db.localSaleEvents);
  $$LocalBrandAmbassadorsTableTableManager get localBrandAmbassadors =>
      $$LocalBrandAmbassadorsTableTableManager(_db, _db.localBrandAmbassadors);
  $$LocalBranchesTableTableManager get localBranches =>
      $$LocalBranchesTableTableManager(_db, _db.localBranches);
  $$LocalPendingSyncItemsTableTableManager get localPendingSyncItems =>
      $$LocalPendingSyncItemsTableTableManager(_db, _db.localPendingSyncItems);
}
