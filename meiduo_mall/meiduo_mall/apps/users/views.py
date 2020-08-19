from django.shortcuts import render, redirect
from django.views import View
from django import http
import re
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login,authenticate,logout
from django.contrib.auth.mixins import LoginRequiredMixin
from meiduo_mall.utils.response_code import RETCODE
from users.models import User
from django_redis import get_redis_connection
class EmailView(View):
    def put(self,request):
        pass
class UserInfoView(LoginRequiredMixin,View):
    """用户中心"""
    def get(self,request):
        """提供用户中心页面"""
        # 如果LoginRequiredMixin判断出用户已登录，那么request.user就是登录用户对象
        context = {
            'username':request.user.username,
            'mobile':request.user.mobile,
            'email':request.user.email,
            'email_active':request.user.email_active
        }
        return render(request,'user_center_info.html',context)
class LogoutView(View):
    """用户退出登录"""
    def get(self,request):
        """实现用户退出的逻辑"""
        #清除状态保持信息
        logout(request)
#         退出登录后重定向到首页
        response = redirect(reverse('contents:index'))
#         删除cookies中的用户名
        response.delete_cookie('username')
#         响应结果
        return response
class LoginView(View):
    """用户名登陆"""
    def get(self,request):
        """提供登录界面"""
        return render(request,'login.html')
    def post(self,request):
        # 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
        #校验参数
        #判断参数是否齐全
        if not all([username,password]):
            return http.HttpResponseForbidden('缺少必传参数')
            # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        #认证登录用户
        user = authenticate(username=username,password=password)
        if user is None:
            return render(request,'login.html',{'account_errmsg':'用户名或密码错误'})
        # 实现状态保持
        login(request,user)
        #设置状态保持的周期
        if remembered !='on':
            #没有记住用户：浏览器会话结束过期
            request.session.set_expiry(0)
        else:
            #记住用户，None表示两周后过期
            request.session.set_expiry(None)
        # 响应登录结果
        # 先取出next
        next = request.GET.get('next')
        if next:
            #重定向到next
            response = redirect(next)
        else:
            response = redirect(reverse('contents:index'))
        #为了实现在首页的右上角展示用户信息，我们需要将用户名缓存到cookie中
        response.set_cookie('username',user.username,max_age=3600 * 24 * 15)
        return response
class RegisterView(View):
    """用户注册"""

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')
    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')
        # 判断参数是否齐全
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断用户名是否是5-20个字符
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')
        # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')
        # 判断两次密码是否一致
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        # 判断短信验证码是否输入正确
        redis_conn = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})
        # 判断是否勾选用户协议
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')
        # 保存注册数据
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        #实现状态保持
        login(request, user)
        # 响应登录结果，重定向到首页
        response = redirect(reverse('contents:index'))
        # 为了实现在首页的右上角展示用户信息，我们需要将用户名缓存到cookie中
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
        return response
class UsernameCountView(View):
    """判断用户名是否重复注册"""

    def get(self, request, username):
        """
        :param request: 请求对象
        :param username: 用户名
        :return: JSON
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})
class MobileCountView(View):
    """判断手机号是否重复注册"""

    def get(self, request, mobile):
        """
        :param request: 请求对象
        :param mobile: 手机号
        :return: JSON
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})