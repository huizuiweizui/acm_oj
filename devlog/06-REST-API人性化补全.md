## 阶段六：REST API 人性化补全

针对已上线的 REST API 层补全了 5 个缺失功能，均在 `judge/api_views.py` 和 `judge/api_urls.py` 中实现。

### Fix 1 — 提交详情补全 `code` 与 `test_results` 字段

**问题**：`SubmissionSerializer` 未暴露 `code` 和 `test_results` 字段，`GET /api/submissions/<id>/` 拿不到源代码和逐测试点结果，用户无法复盘自己的提交。

**修复**（`judge/serializers.py`）：在 `SubmissionSerializer.Meta.fields` 中加入 `code`、`test_results`，并将 `test_results` 纳入 `read_only_fields`。

```python
fields = [
    'id', 'username', 'problem_id', 'problem_title',
    'language', 'status', 'time_used', 'memory_used',
    'error_info', 'ai_feedback', 'test_results', 'code', 'submitted_at',
]
```

---

### Fix 2 — 个人资料编辑接口（PATCH /api/auth/me/）

**问题**：`MeAPIView` 只有 GET，用户无法通过 API 修改 bio、头像颜色、邮箱等信息。

**修复**：为 `MeAPIView` 新增 `patch()` 方法，支持字段：`bio`、`avatar_color`、`avatar_url`（写入 `UserProfile`）、`email`（写入 Django `User`）。返回更新后的完整用户信息。

---

### Fix 3 — 修改密码接口（POST /api/auth/password/）

**新增** `ChangePasswordAPIView`，路由 `POST /api/auth/password/`。

接收 `old_password` 和 `new_password`，校验规则：

- 原密码正确
- 新密码 ≥ 6 位
- 新旧密码不能相同

---

### Fix 4 — 退出登录（POST /api/auth/logout/）+ Token 黑名单

**问题**：无退出登录接口，前端只能删 localStorage，服务端 refresh token 继续有效。

**修复**：

- `settings.py` 新增 `rest_framework_simplejwt.token_blacklist` 至 `INSTALLED_APPS`
- 执行 `python manage.py migrate` 生成 13 张黑名单相关表
- 新增 `LogoutAPIView`：接收 `refresh` token，调用 `RefreshToken(...).blacklist()` 使其服务端失效，无效 token 返回 400

```python
def post(self, request):
    try:
        RefreshToken(request.data.get('refresh')).blacklist()
    except TokenError:
        return Response({'detail': 'token 无效或已过期'}, status=400)
    return Response({'detail': '已退出登录'})
```

---

### Fix 5 — 删除讨论帖 / 回复

**问题**：讨论区发帖和回复后永久存在，无任何删除接口。

**修复**：

- `DiscussionDetailAPIView` 新增 `delete()` 方法，路由复用 `DELETE /api/discussions/<id>/`
- 新增 `DiscussionReplyDeleteAPIView`，路由 `DELETE /api/discussions/<id>/replies/<reply_id>/`

权限规则：只有帖子/回复的作者本人可以删除，他人操作返回 403。删除成功返回 204 No Content。

---
