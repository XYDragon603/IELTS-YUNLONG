export const listeningScript = `Welcome to the Riverside Community Centre. Here is some information about our new photography course. The course begins on Monday, the twelfth of May. Classes take place on the second floor, in room fifteen. Your teacher is Helen Carter. That's C A R T E R. The full course costs eighty pounds, which includes all printed materials. You will need to bring your own camera to each class. Please arrive ten minutes early for your first lesson. We look forward to seeing you.`;

export const listeningQuestions = [
  { id: 'l1', prompt: 'Day of the first class', accepted: ['Monday'], explanation: '录音明确说课程在 Monday 开始。' },
  { id: 'l2', prompt: 'Room number', accepted: ['15', 'fifteen'], explanation: '教室位于二楼，但房间号是 fifteen（15），注意区分楼层与房间号。' },
  { id: 'l3', prompt: 'Teacher’s surname', accepted: ['Carter'], explanation: '老师名为 Helen Carter，姓氏还被逐字拼读为 C-A-R-T-E-R。' },
  { id: 'l4', prompt: 'Course fee in pounds', accepted: ['80', 'eighty', '£80'], explanation: '完整课程费用是 eighty pounds，费用包含印刷资料。' },
  { id: 'l5', prompt: 'Equipment students should bring', accepted: ['camera', 'a camera', 'own camera'], explanation: '录音要求学生带上自己的 camera。' },
];

export const readingParagraphs = [
  'In many cities, residents are turning unused land into community gardens. These shared spaces allow people to grow fruit and vegetables, even when they do not have gardens of their own. A recent project in the fictional town of Westbridge transformed an empty car park into twenty small growing plots.',
  'The Westbridge garden opened in 2022. At first, organisers expected most members to be retired people, but more than half of the first forty members were under thirty. Members pay a small annual fee to cover water and equipment. The local council provided the land free of charge for an initial period of five years.',
  'The benefits extend beyond food production. Members meet every Saturday to share skills and maintain common areas. Several participants say that they now know more of their neighbours. However, no formal study has yet measured whether the garden has improved the physical health of its members.',
  'Not everything has been easy. During the first summer, a lack of rain meant that members had to reduce water use. They responded by installing containers to collect rainwater from a nearby roof. The organisers now advise other groups to plan their water supply before choosing what to plant.',
];

export const readingQuestions = [
  { id: 'r1', prompt: 'The Westbridge garden was built on a former car park.', accepted: ['TRUE'], explanation: '第一段说明该项目将 an empty car park 改造成了种植地。' },
  { id: 'r2', prompt: 'Most of the first members were retired people.', accepted: ['FALSE'], explanation: '第二段说最初四十名成员中超过一半不到三十岁，与组织者原先的预期不同。' },
  { id: 'r3', prompt: 'Members do not have to pay to use the garden.', accepted: ['FALSE'], explanation: '第二段明确提到 members pay a small annual fee。免费提供的是土地。' },
  { id: 'r4', prompt: 'A study has shown that members have become physically healthier.', accepted: ['FALSE'], explanation: '第三段说明 no formal study has yet measured 健康改善情况，与题干声称已有研究证明矛盾。' },
  { id: 'r5', prompt: 'The organisers plan to double the size of the garden next year.', accepted: ['NOT GIVEN'], explanation: '文中没有说明明年扩大花园面积的计划。不能用常识补充文中未提供的信息。' },
];

export const writingPrompt = 'Some people believe that public libraries are no longer necessary because information is available online. Others think that libraries still play an important role in society. Discuss both views and give your own opinion.';
export const speakingPrompt = ['What this skill is', 'When and how you would like to learn it', 'Why you are interested in it', 'And explain how this skill could be useful in your life.'];
