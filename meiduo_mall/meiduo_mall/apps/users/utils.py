#自定义用户认证的后端，实现多账号登录
import password as password
from django.contrib.auth.backends import ModelBackend
import re
from users.models import User
def get_user_by_account(account):
    try:
        if re.match('^1[3-9]\d{9}$',account):
            #手机号登录
            user = User.objects.get(mobile=account)
        else:
            #用户名登录
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user
class UsernameMobileBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = get_user_by_account(username)
        #如果可以查询到用户，就需要校验用户密码是否正确
        if user and user.check_password(password):
            return user
        else:
            return None