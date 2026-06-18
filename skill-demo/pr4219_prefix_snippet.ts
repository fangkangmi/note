// Excerpt from services/apps/data_sink_worker/src/service/activity.service.ts
// Inside ActivityService — method processes a batch of activity payloads and
// returns `resultMap`. `relevantPayloads` starts as the full batch.

    // handleErasure(...) returns false when a member's identities were all removed,
    // and in that case removes the payload from relevantPayloads.
    let promises = []

    const repoPayloads: IActivityProcessData[] = []
    for (const payload of relevantPayloads) {
      if (!handleErasure(payload.activity.member, payload.resultId)) {
        continue
      }
      if (
        payload.activity.objectMember &&
        !handleErasure(payload.activity.objectMember, payload.resultId)
      ) {
        continue
      }
      if (payload.platform === PlatformType.GITLAB || payload.platform === PlatformType.GITHUB) {
        repoPayloads.push(payload)
      } else if (!payload.segmentId) {
        resultMap.set(payload.resultId, {
          success: false,
          err: new UnrepeatableError('No segmentId provided!'),
        })
        // remove this payload from the set we still need to process
        relevantPayloads = relevantPayloads.filter((a) => a.resultId !== payload.resultId)
      }
    }

    // ... (segment lookups for repoPayloads run here and may also resolve/skip payloads) ...
    await Promise.all(promises)

    this.log.trace(
      `[ACTIVITY] We still have ${relevantPayloads.length} activities left to process after finding segments!`,
    )

    const orConditions = relevantPayloads.map((r) => {
      return {
        and: [
          { timestamp: { eq: r.activity.timestamp } },
          { sourceId: { eq: r.activity.sourceId } },
          { platform: { eq: r.activity.platform } },
          { type: { eq: r.activity.type } },
          { channel: { eq: r.activity.channel } },
        ],
      }
    })

    const segmentIds = distinct(relevantPayloads.map((r) => r.segmentId))

    // Check activityRelations to find existing rows; queryActivityRelations builds a
    // SQL WHERE clause from the filter below (the `in` array becomes `timestamp IN (...)`,
    // and `or: orConditions` becomes an OR group of AND groups).
    const existingActivityRelations = await logExecutionTimeV2(
      async () =>
        queryActivityRelations(
          this.pgQx,
          {
            segmentIds,
            filter: {
              and: [
                { timestamp: { in: distinct(relevantPayloads.map((r) => r.activity.timestamp)) } },
                { or: orConditions },
              ],
            },
            limit: relevantPayloads.length,
            noCount: true,
          },
          ['activityId', 'timestamp', 'memberId', 'organizationId'],
        ),
      this.log,
      'queryActivityRelations',
    )

    // ... resultMap is populated from existingActivityRelations and returned ...
    return resultMap
