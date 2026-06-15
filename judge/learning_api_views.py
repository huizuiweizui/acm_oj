"""知识图谱个性化学习路径与题目推荐。

基于 Algorithm + AlgorithmEdge 的「前置依赖」边，对某目标算法做后序 DFS，
得到「前置在前、目标在后」的学习顺序；再用标签启发式把题目挂到算法上，
结合用户 AC 数据给出每个知识点的掌握度与推荐题。
"""
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Algorithm, AlgorithmEdge, Problem, Submission, Tag


def _prereq_order(target_algo_id):
    """后序 DFS 收集目标的全部前置（含自身），前置在前、目标在后；用 visited 防环。"""
    visited, order = set(), []

    def dfs(aid):
        if aid in visited:
            return
        visited.add(aid)
        for tid in (AlgorithmEdge.objects
                    .filter(source__algo_id=aid, edge_type='prerequisite')
                    .values_list('target__algo_id', flat=True)):
            dfs(tid)
        order.append(aid)

    dfs(target_algo_id)
    return order


def _match_tag_ids(algo, all_tags):
    """启发式：标签名与算法名/类别相关（双向子串或类别相等）。
    缺少 Problem↔Algorithm 显式关联时的折中做法。"""
    name, cat = algo.name or '', algo.category or ''
    return [t.id for t in all_tags
            if t.name and (t.name in name or name in t.name or t.name == cat)]


class LearningPathAPIView(APIView):
    """GET /api/algorithms/<algo_id>/learning-path/
    返回到该算法的前置学习路径，每节点附掌握度与推荐题。"""
    permission_classes = [IsAuthenticated]

    def get(self, request, algo_id):
        target = get_object_or_404(Algorithm, algo_id=algo_id)
        order = _prereq_order(target.algo_id)
        algos = {a.algo_id: a for a in Algorithm.objects.filter(algo_id__in=order)}
        all_tags = list(Tag.objects.all())

        ac_ids = set(Submission.objects.filter(user=request.user, status='AC')
                     .values_list('problem_id', flat=True).distinct())

        path = []
        for aid in order:
            algo = algos.get(aid)
            if not algo:
                continue
            tag_ids = _match_tag_ids(algo, all_tags)
            problems = []
            if tag_ids:
                problems = list(Problem.objects.filter(tags__id__in=tag_ids, is_published=True)
                                .distinct().values('id', 'title', 'difficulty')[:30])
            total = len(problems)
            solved = sum(1 for p in problems if p['id'] in ac_ids)
            path.append({
                'algo_id': algo.algo_id,
                'name': algo.name,
                'category': algo.category,
                'difficulty': algo.difficulty,
                'is_target': aid == target.algo_id,
                'problem_count': total,
                'solved_count': solved,
                # 关联题解过半数视为掌握；无关联题目则无法判定（False）
                'mastered': total > 0 and solved >= max(1, total // 2),
                'recommend': [p for p in problems if p['id'] not in ac_ids][:3],
            })

        return Response({
            'target': {'algo_id': target.algo_id, 'name': target.name},
            'path': path,
        })
