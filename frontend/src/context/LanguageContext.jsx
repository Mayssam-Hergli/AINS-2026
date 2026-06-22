import { createContext, useContext, useState } from 'react'

const T = {
  fr: {
    dir: 'ltr',
    landing: {
      tagline: 'Connaître votre trajectoire. Choisir votre chemin.',
      cta_start: 'Commencer',
      cta_login: 'Se connecter',
      partners: 'Partenaires & Sponsors',
    },
    login: {
      title: 'Connexion',
      subtitle: "Plateforme IA pour l'Entrepreneuriat Tunisien",
      email: 'Email',
      email_ph: 'vous@exemple.com',
      password: 'Mot de passe',
      password_ph: '••••••••',
      submit: 'Se connecter',
      loading: 'Connexion...',
      no_account: "Pas encore de compte ?",
      register_link: 'Créer un compte',
      error_default: 'Identifiants incorrects',
    },
    register: {
      title: 'Créer un compte',
      subtitle: "Plateforme IA pour l'Entrepreneuriat Tunisien",
      email: 'Email',
      email_ph: 'vous@exemple.com',
      password: 'Mot de passe',
      password_ph: 'Minimum 8 caractères',
      confirm: 'Confirmer le mot de passe',
      confirm_ph: '••••••••',
      submit: 'Créer mon compte',
      loading: 'Création...',
      has_account: 'Déjà un compte ?',
      login_link: 'Se connecter',
      error_mismatch: 'Les mots de passe ne correspondent pas',
      error_short: 'Le mot de passe doit contenir au moins 8 caractères',
      error_default: 'Erreur lors de la création du compte',
    },
    nav: {
      dashboard: 'Tableau de bord',
      assistant: 'Assistant',
      logout: 'Déconnexion',
      partners: 'Partenaires',
    },
  },
  ar: {
    dir: 'rtl',
    landing: {
      tagline: 'اعرف مسارك. اختر طريقك.',
      cta_start: 'ابدأ الآن',
      cta_login: 'تسجيل الدخول',
      partners: 'الشركاء والرعاة',
    },
    login: {
      title: 'تسجيل الدخول',
      subtitle: 'منصة الذكاء الاصطناعي لريادة الأعمال التونسية',
      email: 'البريد الإلكتروني',
      email_ph: 'example@email.com',
      password: 'كلمة المرور',
      password_ph: '••••••••',
      submit: 'دخول',
      loading: 'جارٍ الدخول...',
      no_account: 'ليس لديك حساب؟',
      register_link: 'إنشاء حساب',
      error_default: 'بيانات الدخول غير صحيحة',
    },
    register: {
      title: 'إنشاء حساب',
      subtitle: 'منصة الذكاء الاصطناعي لريادة الأعمال التونسية',
      email: 'البريد الإلكتروني',
      email_ph: 'example@email.com',
      password: 'كلمة المرور',
      password_ph: '8 أحرف على الأقل',
      confirm: 'تأكيد كلمة المرور',
      confirm_ph: '••••••••',
      submit: 'إنشاء حسابي',
      loading: 'جارٍ الإنشاء...',
      has_account: 'لديك حساب بالفعل؟',
      login_link: 'تسجيل الدخول',
      error_mismatch: 'كلمات المرور غير متطابقة',
      error_short: 'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل',
      error_default: 'حدث خطأ أثناء إنشاء الحساب',
    },
    nav: {
      dashboard: 'لوحة التحكم',
      assistant: 'المساعد',
      logout: 'تسجيل الخروج',
      partners: 'الشركاء',
    },
  },
}

const LanguageContext = createContext(null)

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState('fr')
  const toggleLang = () => setLang((l) => (l === 'fr' ? 'ar' : 'fr'))
  return (
    <LanguageContext.Provider value={{ lang, t: T[lang], toggleLang }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLang = () => useContext(LanguageContext)
