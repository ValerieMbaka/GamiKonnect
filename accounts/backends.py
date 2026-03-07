from django.contrib.auth.backends import BaseBackend
from .models import Gamer, ShopOwner

class FirebaseBackend(BaseBackend):
    def authenticate(self, request, uid=None):
        try:
            # Try to find as Gamer first
            return Gamer.objects.get(uid=uid)
        except Gamer.DoesNotExist:
            try:
                # Then try ShopOwner
                return ShopOwner.objects.get(uid=uid)
            except ShopOwner.DoesNotExist:
                return None

    def get_user(self, user_id):
        try:
            # Try to find as Gamer first
            return Gamer.objects.get(pk=user_id)
        except Gamer.DoesNotExist:
            try:
                # Then try ShopOwner
                return ShopOwner.objects.get(pk=user_id)
            except ShopOwner.DoesNotExist:
                return None