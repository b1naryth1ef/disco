from disco.types.permissions import Permissions, PermissionValue


def test_permission_value_can():
    admin_perms = PermissionValue(
        Permissions.ADMINISTRATOR
    )

    assert admin_perms.administrator

    # Admin can do everything
    for key in Permissions.keys():
        assert admin_perms.can(getattr(Permissions, key))

    manage_channels_perms = PermissionValue(
        Permissions.MANAGE_CHANNELS,
    )

    assert not manage_channels_perms.administrator
    assert manage_channels_perms.manage_channels


def test_permission_value_mutation():
    no_perms = PermissionValue()
    assert not no_perms.can(Permissions.SEND_MESSAGES)

    no_perms.send_messages = True
    assert no_perms.can(Permissions.SEND_MESSAGES)


def test_permission_value_accepts_permission_value():
    perms = PermissionValue(Permissions.ADMINISTRATOR)

    new_perms = PermissionValue(perms)
    assert new_perms.administrator

    assert not new_perms.manage_channels
    new_perms.add(PermissionValue(Permissions.MANAGE_CHANNELS))
    assert new_perms.manage_channels

    new_perms.sub(PermissionValue(Permissions.MANAGE_CHANNELS))
    assert not new_perms.manage_channels
