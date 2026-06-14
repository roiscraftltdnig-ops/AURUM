# Example Onboarding Flows

## Beginner

1. User asks a basic crypto, blockchain, or ROISCRAFT question.
2. AI explains only the first layer.
3. AI offers format choice: quick explanation, video, presentation, or team discussion.
4. AI routes to beginner community after initial intent is confirmed.
5. Memory records viewed content and prevents duplicate video pushes.

## Intermediate

1. User asks about ecosystem participation.
2. AI asks whether they are interested in Aurum Foundation, Bytnet, or the broader ROISCRAFT ecosystem.
3. AI retrieves trusted documents for that portfolio.
4. AI provides a contextual answer and recommends an education journey.
5. AI tracks engagement score and viewed documents.

## Advanced

1. User asks about tokenomics, governance, validators, liquidity, or ecosystem strategy.
2. AI switches to advanced explanations.
3. AI offers advanced group access if configured.
4. AI creates an engagement event for strategic interest.
5. Repeated engagement can trigger admin review.

## High Intent

1. User mentions investing, capital, allocation, partnership, sponsorship, VIP, or collaboration.
2. AI creates an admin task.
3. AI sends Telegram admin alert.
4. AI asks for phone, email, country, and area of interest.
5. Admin follows up and marks the task in progress or completed.

## Duplicate Content Handling

If `aurum_intro_video_sent` is true, the AI should not resend the same video automatically. It should say:

> Previously, we shared the Aurum introduction video with you. Would you like a quick summary, deeper explanation, advanced presentation, or replay the introduction video?

