from core.models import Roles, RoleFeature
from core.role_config import ROLE_FEATURES

def populate_role_features():
    for role_name, features in ROLE_FEATURES.items():
        try:
            role = Roles.objects.get(name=role_name)
        except Roles.DoesNotExist:
            print(f"Role '{role_name}' does not exist. Skipping.")
            continue
        obj, created = RoleFeature.objects.get_or_create(role=role)
        for feature, value in features.items():
            setattr(obj, feature, value)
        obj.save()
        print(f"{'Created' if created else 'Updated'} RoleFeature for {role_name}")

if __name__ == "__main__":
    populate_role_features()
    print("RoleFeature population complete.")
