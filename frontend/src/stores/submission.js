import { ref } from 'vue'
import { defineStore } from 'pinia'
import { getSubmission } from '@/api/submissions'

export const useSubmissionStore = defineStore('submission', () => {
  const current = ref(null)
  const polling = ref(false)
  let _timer = null

  function startPolling(submissionId) {
    current.value = { id: submissionId, status: 'Pending' }
    polling.value = true
    _poll(submissionId)
  }

  async function _poll(id) {
    try {
      const { data } = await getSubmission(id)
      current.value = data
      if (data.status === 'Pending' || data.status === 'Judging') {
        _timer = setTimeout(() => _poll(id), 2000)
      } else {
        polling.value = false
      }
    } catch {
      polling.value = false
    }
  }

  function stopPolling() {
    clearTimeout(_timer)
    polling.value = false
  }

  return { current, polling, startPolling, stopPolling }
})
