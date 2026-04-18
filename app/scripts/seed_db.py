import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal

from app.models import (
    RoleModel,
    PermissionModel,
    RolePermissionMap,
    UserModel,
    UserDetailModel,
)


# ========== HELPERS ==========


async def get_existing_map(db, model, field, values):
    print("\n[HELPER] Fetching existing records...")

    result = await db.execute(select(model).where(field.in_(values)))
    rows = result.scalars().all()

    data = {}

    for row in rows:
        key = getattr(row, field.key)
        data[key] = row

    print(f"[HELPER] Found {len(data)} existing records")

    return data


# ========== ROLES ==========


async def seed_roles(db):
    print("\n========== SEEDING ROLES ==========")

    roles = ["user", "admin", "theatre_admin"]

    existing = await get_existing_map(db, RoleModel, RoleModel.role, roles)

    missing = []
    for role in roles:
        if role not in existing:
            print(f"[ROLES] Missing role → {role}")
            missing.append(role)
        else:
            print(f"[ROLES] Already exists → {role}")

    if len(missing) > 0:
        print(f"[ROLES] Inserting {len(missing)} new roles")

        new_roles = []
        for role in missing:
            print(f"[ROLES] Creating role → {role}")
            new_roles.append(RoleModel(role=role))

        db.add_all(new_roles)
        await db.flush()

        print("[ROLES] Insert completed")
    else:
        print("[ROLES] No new roles to insert")

    return await get_existing_map(db, RoleModel, RoleModel.role, roles)


# ========== PERMISSIONS ==========


async def seed_permissions(db):
    print("\n========== SEEDING PERMISSIONS ==========")

    permissions = [
        "create-user",
        "read-users",
        "create-theatre",
        "read-theatres",
        "delete-theatre",
        "create-movie",
        "read-movies",
        "delete-movie",
        "create-layout",
        "create-screen",
        "delete-screen",
        "create-show",
        "delete-show",
    ]

    existing = await get_existing_map(
        db, PermissionModel, PermissionModel.permission, permissions
    )

    missing = []
    for permission in permissions:
        if permission not in existing:
            print(f"[PERMISSION] Missing → {permission}")
            missing.append(permission)
        else:
            print(f"[PERMISSION] Already exists → {permission}")

    if len(missing) > 0:
        print(f"[PERMISSION] Inserting {len(missing)} new permissions")

        new_permissions = []
        for permission in missing:
            print(f"[PERMISSION] Creating → {permission}")
            new_permissions.append(PermissionModel(permission=permission))

        db.add_all(new_permissions)
        await db.flush()

        print("[PERMISSION] Insert completed")
    else:
        print("[PERMISSION] No new permissions to insert")

    return await get_existing_map(
        db, PermissionModel, PermissionModel.permission, permissions
    )


# ========== ROLE-PERMISSION MAPPING ==========


async def seed_role_permissions(db, roles, permissions):
    print("\n========== SEEDING ROLE-PERMISSION MAPPING ==========")

    theatre_admin_permissions = [
        "create-layout",
        "create-screen",
        "delete-screen",
        "create-show",
        "delete-show",
    ]

    theatre_admin_id = roles["theatre_admin"].id
    print(f"[ROLE-PERM] theatre_admin ID → {theatre_admin_id}")

    permission_ids = []
    for perm in theatre_admin_permissions:
        pid = permissions[perm].id
        print(f"[ROLE-PERM] theatre_admin needs → {perm} (id={pid})")
        permission_ids.append(pid)

    await insert_role_permissions_if_missing(db, theatre_admin_id, permission_ids)

    # ADMIN → ALL
    admin_id = roles["admin"].id
    print(f"[ROLE-PERM] admin ID → {admin_id}")

    all_permission_ids = []
    for perm in permissions:
        pid = permissions[perm].id
        print(f"[ROLE-PERM] admin gets → {perm} (id={pid})")
        all_permission_ids.append(pid)

    await insert_role_permissions_if_missing(db, admin_id, all_permission_ids)


async def insert_role_permissions_if_missing(db, role_id, permission_ids):
    print(f"\n[ROLE-PERM] Checking existing mappings for role_id={role_id}")

    result = await db.execute(
        select(RolePermissionMap.permission_id).where(
            RolePermissionMap.role_id == role_id
        )
    )

    existing_ids_list = result.scalars().all()

    existing_ids = set()
    for eid in existing_ids_list:
        existing_ids.add(eid)

    print(f"[ROLE-PERM] Existing mappings count → {len(existing_ids)}")

    missing_ids = []
    for pid in permission_ids:
        if pid not in existing_ids:
            print(f"[ROLE-PERM] Missing mapping → permission_id={pid}")
            missing_ids.append(pid)
        else:
            print(f"[ROLE-PERM] Already mapped → permission_id={pid}")

    if len(missing_ids) > 0:
        print(f"[ROLE-PERM] Inserting {len(missing_ids)} mappings")

        new_mappings = []
        for pid in missing_ids:
            print(f"[ROLE-PERM] Creating mapping role={role_id}, perm={pid}")
            new_mappings.append(RolePermissionMap(role_id=role_id, permission_id=pid))

        db.add_all(new_mappings)
        print("[ROLE-PERM] Insert completed")
    else:
        print("[ROLE-PERM] No new mappings needed")


# ========== USERS ==========


async def seed_users(db, roles):
    print("\n========== SEEDING USERS ==========")

    users_data = [
        ("jaymin.dave@armakuni.com", True, roles["admin"].id),
        ("jaymin4724@gmail.com", True, roles["theatre_admin"].id),
    ]

    emails = []
    for user in users_data:
        emails.append(user[0])

    result = await db.execute(select(UserModel).where(UserModel.email.in_(emails)))

    existing_users_list = result.scalars().all()

    existing_users = {}
    for user in existing_users_list:
        existing_users[user.email] = user

    print(f"[USERS] Existing users count → {len(existing_users)}")

    new_users = []

    for user in users_data:
        email = user[0]
        is_active = user[1]
        role_id = user[2]

        if email not in existing_users:
            print(f"[USERS] Missing → {email}")
            new_users.append(
                UserModel(email=email, is_active=is_active, role_id=role_id)
            )
        else:
            print(f"[USERS] Already exists → {email}")

    if len(new_users) > 0:
        print(f"[USERS] Inserting {len(new_users)} users")
        db.add_all(new_users)
        await db.flush()
        print("[USERS] Insert completed")
    else:
        print("[USERS] No new users to insert")

    result = await db.execute(select(UserModel).where(UserModel.email.in_(emails)))

    users_list = result.scalars().all()

    users_map = {}
    for user in users_list:
        users_map[user.email] = user

    return users_map


# ========== USER DETAILS ==========


async def seed_user_details(db, users):
    print("\n========== SEEDING USER DETAILS ==========")

    user_ids = []
    for user in users.values():
        user_ids.append(user.id)

    result = await db.execute(
        select(UserDetailModel.user_id).where(UserDetailModel.user_id.in_(user_ids))
    )

    existing_ids_list = result.scalars().all()

    existing_ids = set()
    for uid in existing_ids_list:
        existing_ids.add(uid)

    print(f"[USER-DETAILS] Existing count → {len(existing_ids)}")

    missing_ids = []
    for uid in user_ids:
        if uid not in existing_ids:
            print(f"[USER-DETAILS] Missing → user_id={uid}")
            missing_ids.append(uid)
        else:
            print(f"[USER-DETAILS] Already exists → user_id={uid}")

    if len(missing_ids) > 0:
        print(f"[USER-DETAILS] Inserting {len(missing_ids)} records")

        new_details = []
        for uid in missing_ids:
            new_details.append(UserDetailModel(user_id=uid))

        db.add_all(new_details)
        print("[USER-DETAILS] Insert completed")
    else:
        print("[USER-DETAILS] No new records needed")


# ========== MAIN ==========


async def seed():
    print("\n========== STARTING DB SEED ==========")

    async with AsyncSessionLocal() as db:
        async with db.begin():

            roles = await seed_roles(db)
            permissions = await seed_permissions(db)

            await seed_role_permissions(db, roles, permissions)

            users = await seed_users(db, roles)
            await seed_user_details(db, users)

        await db.commit()

    print("\n========== DB SEED COMPLETED ==========")


if __name__ == "__main__":
    asyncio.run(seed())
