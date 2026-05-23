export const STEP_META = {
  cause: { num: 1, label: '原因', sub: '為什麼會發生', q: '為什麼這場衝突會被推到戰場上？' },
  decision: { num: 2, label: '決策', sub: '誰做了選擇', q: '關鍵人物做了哪些判斷？' },
  action: { num: 3, label: '行動', sub: '用了什麼計策', q: '戰場上採取了哪些行動？' },
  result: { num: 4, label: '結果', sub: '局勢怎麼變', q: '勝負如何改變後續局勢？' }
};

export const STEP_ORDER = ['cause', 'decision', 'action', 'result'];

export const STEP_CATEGORIES = {
  cause: ['story'],
  decision: ['command', 'strategy'],
  action: ['military', 'strategy'],
  result: ['defeat']
};

export const BATTLES = [
  {
    key: 'guandu',
    name: '官渡之戰',
    nodeNames: ['官渡之戰', '官渡曹營攻防', '官渡'],
    chapters: [22, 30],
    period: '21-30 章 · 官渡前後',
    sideA: { label: '袁紹方', camp: 'lords', leader: '袁紹', lookup: '袁紹勢力', members: ['顏良', '文醜', '許攸', '袁譚', '袁尚'] },
    sideB: { label: '曹操方', camp: 'wei', leader: '曹操', members: ['荀彧', '荀攸', '張遼', '許褚'] },
    outcome: '曹操勝',
    coreQuestion: '袁紹兵多糧足，為什麼最後被曹操打敗？',
    meaning: '三國演義裡以少勝多的代表戰役。資源不是決定勝負的唯一原因，能聽諫言、能用人才的領袖，才是真的強。'
  },
  {
    key: 'chibi',
    name: '赤壁之戰',
    nodeNames: ['赤壁火攻', '赤壁鏖兵', '赤壁'],
    chapters: [43, 50],
    period: '41-50 章 · 赤壁鏖兵',
    sideA: { label: '曹操方', camp: 'wei', leader: '曹操', members: ['蔡瑁', '張遼', '許褚'] },
    sideB: { label: '孫劉聯軍', camp: 'wu', leader: '周瑜', members: ['孫權', '劉備', '諸葛亮', '魯肅', '黃蓋'] },
    outcome: '孫劉聯軍勝',
    coreQuestion: '曹操南征聲勢浩大，為什麼會在赤壁被反推？',
    meaning: '赤壁把戰力、地利、情報與聯盟都放在同一個局面裡，說明弱勢方若能協作，也能改寫大勢。'
  },
  {
    key: 'changban',
    name: '長坂坡',
    nodeNames: ['長坂坡亂軍突圍', '當陽長坂大戰', '長坂橋對峙', '長坂坡'],
    chapters: [41, 42],
    period: '41-50 章 · 撤退與保全',
    sideA: { label: '曹操方', camp: 'wei', leader: '曹操', members: ['張遼', '許褚', '文聘'] },
    sideB: { label: '劉備方', camp: 'shu', leader: '劉備', members: ['趙雲', '張飛', '關羽'] },
    outcome: '劉備脫險',
    coreQuestion: '劉備兵敗撤退，為什麼長坂坡反而成了英雄舞台？',
    meaning: '長坂坡的重點不是殲滅敵軍，而是在敗局中保住核心人物與民心，讓撤退仍然有戰略價值。'
  },
  {
    key: 'hulao',
    name: '虎牢關',
    nodeNames: ['虎牢關之戰', '虎牢關'],
    chapters: [5, 6],
    period: '1-10 章 · 英雄起義',
    sideA: { label: '董卓方', camp: 'lords', leader: '呂布', members: ['董卓', '華雄', '張濟'] },
    sideB: { label: '諸侯聯軍', camp: 'lords', leader: '劉備', members: ['關羽', '張飛', '曹操', '孫堅'] },
    outcome: '諸侯逼退董卓',
    coreQuestion: '各路諸侯互不信任，為什麼仍能逼近虎牢關？',
    meaning: '虎牢關把群雄的鬆散聯盟與個人武勇放在同一張沙盤上，英雄登場比組織協調更醒目。'
  },
  {
    key: 'xiapi',
    name: '下邳',
    nodeNames: ['下邳之戰', '下邳'],
    chapters: [17, 19],
    period: '11-20 章 · 群雄角力',
    sideA: { label: '曹劉聯軍', camp: 'wei', leader: '曹操', members: ['劉備', '關羽', '張飛', '郭嘉'] },
    sideB: { label: '呂布方', camp: 'lords', leader: '呂布', members: ['陳宮', '高順', '張遼'] },
    outcome: '呂布敗亡',
    coreQuestion: '呂布武力強大，為什麼守不住下邳？',
    meaning: '下邳顯示個人勇武不能取代組織信任。當部屬離心、決策反覆，城池再堅也會失守。'
  },
  {
    key: 'jingnan',
    name: '荊南四郡',
    nodeNames: ['荊南諸縣', '長沙', '桂陽', '武陵', '零陵'],
    chapters: [52, 53],
    period: '51-60 章 · 荊南西川',
    sideA: { label: '劉備方', camp: 'shu', leader: '劉備', members: ['諸葛亮', '張飛', '趙雲', '關羽'] },
    sideB: { label: '荊南守將', camp: 'lords', leader: '韓玄', members: ['黃忠', '魏延', '金旋', '趙範', '劉度'] },
    outcome: '劉備取得荊南',
    coreQuestion: '赤壁後劉備為什麼要快速南取四郡？',
    meaning: '荊南四郡讓劉備從寄居者變成有地盤的政治勢力，也讓後續入蜀有了真正的根基。'
  }
];

export function getBattleByKey(key) {
  return BATTLES.find(item => item.key === key) || BATTLES[0];
}
