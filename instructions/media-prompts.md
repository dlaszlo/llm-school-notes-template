# Reusable learning-media prompts

These shared prompts implement [media workflows](media-workflows.md) under [AGENTS.md](../AGENTS.md). Read only the prompt for the requested stage. Fill placeholders from the current request, local profile and verified sources; the template supplies no learner, subject, account or spending authorization. The original Hungarian prompt language is preserved as functional text; `{wiki_nyelv}` is the configured learner-facing language. Never pass raw private profile details that are irrelevant to a generation request.

## Content scope

```text
Feladat: {keres}. Tanuló: {relevans_profil}. Források: {wikioldalak_es_verziok}. Aktuális tanulási döntés és célzott követelményhelyek: {tanulasi_hatokor_es_kovetelmenyek}.
Olvasd végig az érintett jegyzeteket és kövesd a szükséges forráshivatkozásokat. Ne generálj médiát.
Készíts rövid munkalapot ezekkel a mezőkkel:
CONTEXT: Mi ez a téma, milyen tágabb kérdésbe tartozik, miért érdemes megérteni? Csak a megértéshez szükséges háttérdimenziókat válaszd ki a forrásból.
SCOPE: Ellenőrizd a tanulási döntést az aktuális leckével: relevancia, elvárt műveleti mélység, indokolt emelt szint, opcionális kitekintés. Követelményből csak pontos helyhez és szinthez kötött elvárást használj, ne adj hozzá teljes tantervi témakört.
GOAL: Mit tudjon a tanuló az anyag után saját szavaival elmagyarázni vagy elvégezni?
BRIDGE: Mely előfeltételek szükségesek? Mi igazoltan ismert a profilból, és mit kell itt röviden megtanítani?
CORE: A tanulási célhoz nélkülözhetetlen állítások, kapcsolatok vagy műveleti lépések, rövid azonosítóval. Mindegyikhez forráshely, megőrzendő feltétel és bizonyossági státusz tartozzon.
QUESTIONS: Mely fontos miért/hogyan/mikor kérdésekre adjon választ az anyag? Írd melléjük a forrásból alátámasztott válasz lényegét.
OPTIONAL: Másodlagos részletek, saját szemléltető példák és indokolt kihagyások.
GAPS: Hiányzó bizonyítékok, ellentmondások, bizonytalan olvasatok.
A fontosságot a felhasználói cél, az órai hangsúly és a megértési függőség határozza meg, ne a látványosság.
A saját példát jelöld példaként; feltételezést és kiegészítést ne emelj észrevétlenül biztos tananyagi ténnyé.
Ha egy nélkülözhetetlen hiány nem tisztázható a rendelkezésre álló bizonyítékból, állj meg a véglegesítés előtt és nevezd meg, mi szükséges.
```

## Podcast script

```text
Írj {wiki_nyelv} alapnyelvű podcastot a {tartalmi_szerzodes} alapján, a {profil} tanulójának. A célnyelvi példák és funkcionális szövegek őrizzék meg eredeti nyelvüket. Kért időkeret: {keret_vagy_nincs}.
Előbb készíts témablokktervet: blokkonként tanulási pont, szükséges előfeltétel, kapcsolódó CORE-elemek, fontos kérdések, átvezetés. Becsüld meg a hosszt; ne nyújtsd ismétléssel.
Ezután írd meg a TELJES párbeszédet, megszólalásazonosítókkal, Anna és Bence között.
A nyitás természetes beszélgetésben nevezze meg a témát és a tágabb tananyagi területet, az alapkérdést és annak jelentőségét. Add meg a CONTEXT ténylegesen szükséges részét; a hallgató most találkozhat először a témával.
A nélkülözhetetlen fogalmakat használat előtt vagy az első használatkor érthetően vezesd be. Az ismeretlen jelöléseket mondd ki és magyarázd meg.
Minden érdemi témablokk magyarázata után beszéljétek meg a hozzá tartozó fontos kérdéseket és a válaszok miértjét. Lehet rövid, szelíd felidéző kérdés és gondolkodási szünet, utána magyarázat. Ne váljon minden mondat kikérdezéssé, és ne ismételj merev blokkzáró formulát.
Mindkét szereplő kérdezhet és magyarázhat. Legyenek barátságosak, kíváncsiak és természetesek; ne gyárts nézeteltérést, túlzó lelkesedést vagy állandó helyeslést.
A kapcsolatok kép nélkül is követhetők legyenek. Kerüld az olyan utalást, hogy "itt látható". A szemléltető helyzetet szóban is azonosítsd példaként.
A lezárás kapcsolja össze a fő gondolatokat, és térjen vissza az alapkérdéshez.
Add vissza a párbeszédet és a CORE-elemek megszólalásokhoz rendelt lefedettségét. Még ne indíts TTS-t.
```

## Presentation storyboard

```text
A {tartalmi_szerzodes} alapján tervezz önállóan tanulható, {wiki_nyelv} nyelvű PDF-et a {profil} tanulójának. Őrizd meg a célnyelvi példák és funkcionális szövegek eredeti nyelvét. Diaszám: {kert_vagy_javasolt}.
Először a TELJES storyboardot add vissza. Oldalanként: cím, egy összetartozó tanulási pont, pontos látható szöveg, vizuális magyarázat, CORE-azonosítók/forráshelyek, kapcsolat az előző és következő oldallal.
Az első oldalakon röviden helyezd el a témát és vezesd be a szükséges alapokat. Ezután magyarázz fokozatosan; a fontos kérdésekre az oldalak tartalma adjon választ.
Egy oldal több összetartozó részletet is taníthat. Az olvasó külső előadó és rejtett jegyzet nélkül értse a magyarázatot, az ábrák jelentését és a következtetést.
Ne készíts darabszámkitöltő címlapot vagy záróoldalt. Ellenőrizd a teljes lefedettséget és a követhető sorrendet, mielőtt egyedi képpromptokat írsz.
Rögzíts közös megjelenést: címhely, szöveghierarchia, következetes fogalomszínek, illusztráció és forrásjelölés. A tartalom határozza meg az oldal kompozícióját.
```

## Infographic layout

```text
A {tartalmi_szerzodes} alapján tervezz {wiki_nyelv} nyelvű infografikát a {profil} tanulójának. Őrizd meg a célnyelvi példák és funkcionális szövegek eredeti nyelvét.
Fogalmazd meg a fő üzenetet és az egy pillantással felismerhető szerkezetet. A CORE valamennyi elemének legyen helye; a részletek fontossági hierarchiája látszódjon.
Válassz a témához illő vizuális rendezést. Add meg a címeket, pontos rövid feliratokat, olvasási sorrendet, csoportokat, kapcsolatokat és feltételeket.
Az elrendezésből legyen világos, mi mivel függ össze és miért; nyilat csak jelentéssel használj. A szükséges alapfogalmat röviden magyarázd meg.
Válaszd külön a megértéshez szükséges fontos tartalmat az összes elérhető adattól. Ne zsúfold rá a teljes jegyzetet.
Ha minden nélkülözhetetlen elem csak apró szöveggel férne el, javasolj szűkebb fókuszt vagy több külön anyagot. Ennek egyeztetése előtt ne generálj képet és ne hagyj ki csendben lényeges tartalmat.
```

## Printable study notes

```text
Készíts nyomtatható tanulási jegyzetet a {tartalmi_szerzodes} és az aktuális {wikioldalak_es_verziok} alapján, a {profil} tanulójának. Kért oldalkeret: {keret_vagy_nincs}.
Először tervezz fejezetsorrendet és becsült terjedelmet. Legyen rövid eligazítás, tanulási cél, a szükséges alapfogalmak bevezetése, összefüggő magyarázat és indokolt kidolgozott példa. A CORE minden elemének legyen helye; a BRIDGE magyarázata ne maradjon link mögött.
Őrizd meg a tanult tartalom, a magyarázat és az opcionális mélyítés forrásjelölését. Emelt követelmény ne bővítse automatikusan a lecke magját. A {wiki_nyelv} nyelvű magyarázat mellett őrizd meg a célnyelvi példákat és funkcionális szövegeket.
Válaszd ki azokat a ténylegesen ellenőrzött ábrákat, amelyek a papíron tanuláshoz szükségesek; magyarázd meg a jelöléseket a szövegben. Pontos szakmai ábra maradhat SVG/vektoros eredetű. A fejezetek ne igényeljenek kattintást, rejtett kommentet vagy külső előadót a megértéshez.
Zárj rövid összefoglalóval és néhány célhoz illő önellenőrző kérdéssel. A számozott válaszok és a megoldásmenet külön utolsó részbe kerüljenek, lehetőleg új oldalon. A kérdés tanítsa vagy ellenőrizze a vállalt célt, ne hozzon be új, meg nem magyarázott tananyagot.
A kimenet álló A4-es, kijelölhető és kereshető törzsszövegű PDF legyen. Ne generált képként készítsd el az egész oldalakat. Használj takarékos, szürkeárnyalatban is értelmezhető megjelenést és szerény jegyzetelési helyet. Ha a kért terjedelem szűk, ne zsugorítsd a betűt és ne hagyj ki szükséges lépést; jelezd a természetes bontást vagy szűkebb fókuszt.
Ellenőrizd a forrásokkal a teljes szöveget, a kérdés-válasz párokat és a CORE lefedettségét. A kész PDF minden oldalát rendereld és nézd meg, továbbá ellenőrizd a szövegkinyerést. Add vissza a dokumentumot, a forrásváltozatokat és az ellenőrzés rövid rekordját.
```

## Image generation

```text
Készíts egy {infografika_vagy_dia} képet a következő lezárt tervből: {ellenorzott_terv}.
Közös megjelenés: {stilus}. Pontos feliratok, nyelvük és hierarchiájuk: {szoveglista}.
Ábrázolandó elemek és kapcsolatok: {elemek_iranyok_feltetelek}. Olvasási sorrend: {sorrend}.
Tervezett fizikai méret: {a4_tajolas}; legalább 10 mm szabad biztonsági margó. A végleges nyomtatási méretben legyen olvasható minden kötelező felirat.
Tartsd meg az ékezeteket, számokat, neveket és feltételeket. Ne adj hozzá új tényt, szereplőt vagy kapcsolatot. A díszítés ne keltsen téves tartalmi benyomást.
```

## Independent review and repair

```text
Vizsgáld meg a {tenyleges_kimenet} teljes tartalmát. Az összehasonlítás alapja a {tartalmi_szerzodes} és az eredeti {forrashelyek}, ne csak a generáló prompt legyen.
Először ellenőrizd, hogy a szerződés hű-e a forrásokhoz; a hibás tervet a pontos képgenerálás sem javítja meg.
Keresd a kihagyott CORE-elemeket, hozzáadott állításokat, elveszett feltételeket, hibás neveket/számokat, képi irányokat, magyarázat nélkül használt fogalmakat és ugrásokat.
Válaszold meg kizárólag a kész anyagból a tanulási célt és a kulcskérdéseket. Ne egészítsd ki fejben hiányzó háttértudással. A modell válasza ellenőrzési jelzés, nem tanulói megértés bizonyítéka.
Képnél vizsgáld a tényleges feliratokat, nyilakat, vágásokat és A4-olvashatóságot. PDF-nél minden oldalt és a teljes sorrendet; tanulási jegyzetnél a kijelölhető szöveget, szürkeárnyalatos olvashatóságot és a külön válaszrész helyességét is. Hangnál a szöveghűséget, érthetőséget, kiejtést, hangazonosságot és illesztéseket.
Hibánként add meg: pontos hely, megfigyelés, forrás szerinti helyes állapot, szükséges változtatás. Az el nem érhető bizonyítékot jelöld ellenőrizetlennek.
Ha megfelel, állj meg. Javításhoz csak konkrét hibából indulj ki, nevezd meg a megőrzendő helyes részeket. Utána az egész érintett képet/oldalt/szegmenst és a kapcsolódó átmeneteket vizsgáld újra.
```

## Speech synthesis

Use stable fictional speaker names and the configured voice mapping throughout the recording. The example dialogue names Anna and Bence are fictional characters, not learner identities. Check pronunciation aids against evidence before sending the script to TTS.

```text
A megadott megszólalást mondd el természetesen, nyugodt, érdeklődő hangon. Alapnyelv: {wiki_nyelv}; a jelölt idegen nyelvű példákat saját nyelvükön mondd. Őrizd meg a szöveget; a szereplő nevét, azonosítóját és technikai jelzéseit ne olvasd fel. Kiejtési támpontok: {ellenorzott_kiejtesek}.
```
