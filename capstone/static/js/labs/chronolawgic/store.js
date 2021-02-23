import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";
import {router} from "./main.js"

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

// eslint-disable-next-line
const importUrls = urls; // defined in timeline.html
// eslint-disable-next-line
const importChoices = choices; // defined in timeline.html

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        choices: importChoices,
        requestStatus: 'nominal', // can be nominal, success, error, or pending. Prone to race conditions, so use only for user feedback until its improved
        notificationMessage: null,
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: importUrls.chronolawgic_api_create,
            chronolawgic_api_retrieve: importUrls.chronolawgic_api_retrieve,
            chronolawgic_api_update: importUrls.chronolawgic_api_update,
            chronolawgic_api_delete: importUrls.chronolawgic_api_delete,
            static: importUrls.static,
            api_root: importUrls.api_root,
        },
        availableTimelines: [],
        id: 1,
        title: "Timeline Title",
        createdBy: "Editable Text", // (user accts are for auth/logging purposes)
        categories: { }, // Removed from MVP
        events: [ {
                    name: "Event 1",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1880,
                    end_year: 1889,
            },
            {
                    name: "Event 2",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1890,
                    end_year: 1912,
            },
            {
                    name: "Event 3",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1905,
                    end_year: 1930,
            },
            {
                    name: "Event 4",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1922,
                    end_year: 1923,
            },
            {
                    name: "Event 5",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1918,
                    end_year: 1924,
            },
            {
                    name: "Event 6",
                    url: "https://cite.case.law/ill/1/176/",
                    long_description: "Between some time and some other time, this thing happened.",
                    start_year: 1875,
                    end_year: 1878,
            },
        ],
        cases: [
            {
                name: "Case 1",
                subhead: "The first case in the timeline.",
                decision_date: new Date(1893, 11, 17),
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                short_description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                long_description: "Consequuntur eum occaecati aliquam reprehenderit molestias ipsam laudantium. Et quisquam quod eum quia nobis quidem. Veritatis qui nulla rem. Est voluptate expedita sapiente. Qui libero veritatis possimus dolorem sint repudiandae sunt doloremque.\n" +
                    "\n" +
                    "Velit et quas officiis sed vero. Recusandae consequatur vel excepturi totam et excepturi. Est voluptates ipsam velit ut non itaque consequatur veritatis.\n" +
                    "\n" +
                    "Autem exercitationem omnis ducimus molestias. Qui explicabo saepe laborum dolorum ea et. Quidem facilis non ea nemo consectetur velit eos."
            },
            {
                name: "Case 2",
                subhead: "The second case in the timeline.",
                short_description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                decision_date: new Date(1898, 11, 17),
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                long_description: "Consequuntur eum occaecati aliquam reprehenderit molestias ipsam laudantium. Et quisquam quod eum quia nobis quidem. Veritatis qui nulla rem. Est voluptate expedita sapiente. Qui libero veritatis possimus dolorem sint repudiandae sunt doloremque.\n" +
                    "\n" +
                    "Velit et quas officiis sed vero. Recusandae consequatur vel excepturi totam et excepturi. Est voluptates ipsam velit ut non itaque consequatur veritatis.\n" +
                    "\n" +
                    "Autem exercitationem omnis ducimus molestias. Qui explicabo saepe laborum dolorum ea et. Quidem facilis non ea nemo consectetur velit eos."
            },
            {
                name: "Case 3",
                subhead: "The third case in the timeline.",
                short_description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                decision_date: new Date(1921, 11, 17),
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                long_description: "Consequuntur eum occaecati aliquam reprehenderit molestias ipsam laudantium. Et quisquam quod eum quia nobis quidem. Veritatis qui nulla rem. Est voluptate expedita sapiente. Qui libero veritatis possimus dolorem sint repudiandae sunt doloremque.\n" +
                    "\n" +
                    "Velit et quas officiis sed vero. Recusandae consequatur vel excepturi totam et excepturi. Est voluptates ipsam velit ut non itaque consequatur veritatis.\n" +
                    "\n" +
                    "Autem exercitationem omnis ducimus molestias. Qui explicabo saepe laborum dolorum ea et. Quidem facilis non ea nemo consectetur velit eos."
            },
            {
                name: "Case 4",
                subhead: "The fourt case in the timeline.",
                short_description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                decision_date: new Date(1921, 11, 18),
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                long_description: "Consequuntur eum occaecati aliquam reprehenderit molestias ipsam laudantium. Et quisquam quod eum quia nobis quidem. Veritatis qui nulla rem. Est voluptate expedita sapiente. Qui libero veritatis possimus dolorem sint repudiandae sunt doloremque.\n" +
                    "\n" +
                    "Velit et quas officiis sed vero. Recusandae consequatur vel excepturi totam et excepturi. Est voluptates ipsam velit ut non itaque consequatur veritatis.\n" +
                    "\n" +
                    "Autem exercitationem omnis ducimus molestias. Qui explicabo saepe laborum dolorum ea et. Quidem facilis non ea nemo consectetur velit eos."
            },
            {
                name: "Case 5",
                subhead: "The fifth case in the timeline.",
                short_description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                decision_date: new Date(1924, 11, 17),
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                long_description: "Consequuntur eum occaecati aliquam reprehenderit molestias ipsam laudantium. Et quisquam quod eum quia nobis quidem. Veritatis qui nulla rem. Est voluptate expedita sapiente. Qui libero veritatis possimus dolorem sint repudiandae sunt doloremque.\n" +
                    "\n" +
                    "Velit et quas officiis sed vero. Recusandae consequatur vel excepturi totam et excepturi. Est voluptates ipsam velit ut non itaque consequatur veritatis.\n" +
                    "\n" +
                    "Autem exercitationem omnis ducimus molestias. Qui explicabo saepe laborum dolorum ea et. Quidem facilis non ea nemo consectetur velit eos."
            },
        ],
        templateEvent: {
            url: "",
            name: "",
            short_description: "",
            long_description: "",
            start_date: "",
            end_date: "",
            categories: [],
        },
        templateCase: {
            url: "",
            name: "",
            short_description: "",
            long_description: "",
            jurisdiction: "",
            reporter: "",
            end_date: "",
            categories: [],
        }
    },
    mutations: {
        writeTimeline(state) {
            //TODO
            state.placeholder = 9;
        },
        deleteTimeline() {
            //todo
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {

            state.title = json.title;
            state.CreatedBy = json.CreatedBy;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id
        },
        setRequestStatus(state, status) {
            state.requestStatus = status;
        },
        setRequestStatusTerminal(state, status) {
            state.requestStatus = status;
            setTimeout(function () {
                state.requestStatus = "nominal";
            }, 5000);
        },
        setNotificationMessage(state, message) {
            //TODO Someday— make this a queue and let the notifications stack
            state.notificationMessage = message;
            setTimeout(function () {
                state.notificationMessage = null;
            }, 5000);
        },
        addEvent(state, event) {
            state.events.push(event)
            console.log("events update", state.events)
        },
        addCase(state, caselaw) {
            state.cases.push(caselaw)
        },
        updateEvent(state, index, event) {
            state.events[index] = event
        },
        updateCase(state, index, event) {
            state.events[index] = event
        },
        deleteEvent(state, index) {
            state.events.remove(index);
        },
        deleteCase(state, index) {
            state.cases.remove(index);
        }
    },
    getters: {
        cases: state => state.cases,
        choices: state => state.choices,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        notificationMessage: state => state.notificationMessage,
        templateEvent: state => state.templateEvent,
        firstYear: (state)=> {
            const first_event_year = state.events.reduce((min, e) => e.start_year < min ? e.start_year : min, state.events[0].start_year);
            const first_case_year = state.cases.reduce((min, e) => e.decision_date.getFullYear() < min ? e.decision_date.getFullYear() : min, state.cases[0].decision_date.getFullYear());
            return first_case_year < first_event_year ? first_case_year : first_event_year;
        },
        lastYear: (state)=> {
            const last_event_year = state.events.reduce((max, e) => e.end_year > max ? e.end_year : max, state.events[0].end_year);
            const last_case_year = state.cases.reduce((max, e) => e.decision_date.getFullYear() > max ? e.decision_date.getFullYear() : max, state.cases[0].decision_date.getFullYear());
            return last_case_year > last_event_year ? last_case_year : last_event_year;
        },
        events: (state)=> {
            return state.events.sort((a, b) => (a.start_year > b.start_year) ? 1 : -1)
        },
        // eventsByYear: (state) => (year) => {
        //     return state.events.filter(evt => {
        //         return year >= evt.start_year && year >= evt.end_year;
        //     })
        // },
        eventByStartYear: (state) => (year) => {
            return state.events.filter(evt => {
                return evt.start_year === year;
            })
        },
        // eventByName: (state) => (name) => {
        //     return state.events.filter(evt => {
        //         return evt.name === name;
        //     })[0]
        // },
        casesByYear: (state) => (year) => {
            return state.cases.filter(cas => {
                return year === cas.decision_date.getFullYear();
            })
        },
        templateCase: state => state.templateCase,
    },
    actions: {
        serialize: ({state}) => {
            return {
                id: state.id,
                title: state.title,
                CreatedBy: state.CreatedBy,
                categories: state.categories,
                events: state.events,
                cases: state.cases,
            }
        },
        requestCreateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .post(this.state.urls.chronolawgic_api_create)
                .then(response => response.data)
                .then(new_tl => {
                    if (new_tl.status === "ok") {
                        this.dispatch('requestTimelineList');
                        router.push({name: 'timeline', params: {timeline: new_tl.id}})
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', 'Timeline Created')
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestDeleteTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .delete(this.state.urls.chronolawgic_api_delete + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        this.dispatch('requestTimelineList');
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', "Timeline Deleted")
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestUpdateTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .delete(this.state.urls.chronolawgic_api_update + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        this.requestTimelineList();
                        commit('setDeletedStatus', timeline['timeline'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', "Timeline Saved")
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimeline', timeline['timeline'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestTimelineList: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve)
                .then(response => response.data)
                .then(availableTimelines => {
                    if (availableTimelines.status === "ok") {
                        commit('setAvailableTimelines', availableTimelines['timelines'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        }
    }
});
export default store;