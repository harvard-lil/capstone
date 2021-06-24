import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

// eslint-disable-next-line
const importUrls = urls; // defined in timeline.html
// eslint-disable-next-line
const importChoices = choices; // defined in timeline.html
// eslint-disable-next-line
const importUser = user; // defined in timeline.html

importChoices.colors = [
    "#00db67",
    "#ccff6d",
    "#dbc600",
    "#db8f00",
    "#ff8e7a",
    "#ff736c",
    "#e5435c",
    "#986d81",
    "#7e84ff",
    "#3656f6",
    "#2f2f2f",
    "#3e667a",
    "#00b7db",
    "#c4c4c4",
];

// jurisdictions
const jurisdictions = [];
for (let i = 0; i < importChoices.jurisdictions.length; i++) {
    jurisdictions.push(importChoices.jurisdictions[i][1])
}
importChoices.jurisdictions = jurisdictions;

// courts
const courts = [];
for (let i = 0; i < importChoices.courts.length; i++) {
    courts.push({
        slug: importChoices.courts[i][0],
        courtName: importChoices.courts[i][1]
    })
}
importChoices.courts = courts;

function getBestError(error) {
    // eslint-disable-next-line
    // debugger;
    if (error && Object.prototype.hasOwnProperty.call(error, "response") &&
        Object.prototype.hasOwnProperty.call(error.response, "data") &&
        Object.prototype.hasOwnProperty.call(error.response.data, "reason")) {
        if (Object.prototype.hasOwnProperty.call(error.response.data, "details")) {
            return error.response.data.reason + ": " + error.response.data.details
        }
        return error.response.data.reason
    }
    return error
}

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        mobileEventsExpanded: false,
        breakPoint: 'lg',
        user: importUser,
        choices: importChoices,
        requestStatus: 'nominal', // can be nominal, success, error, or pending. Prone to race conditions, so use only for user feedback until its improved
        notificationMessage: null,
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: importUrls.chronolawgic_api_create,
            chronolawgic_api_retrieve: importUrls.chronolawgic_api_retrieve,
            chronolawgic_api_update: importUrls.chronolawgic_api_update,
            chronolawgic_api_delete: importUrls.chronolawgic_api_delete,
            chronolawgic_api_update_admin: importUrls.chronolawgic_api_update_admin,
            chronolawgic_api_create_h2o: importUrls.chronolawgic_api_create_h2o,

            api_delete_category: importUrls.api_delete_category,
            api_add_update_category: importUrls.api_add_update_category,
            api_delete_case: importUrls.api_delete_case,
            api_add_update_case: importUrls.api_add_update_case,
            api_delete_event: importUrls.api_delete_event,
            api_add_update_event: importUrls.api_add_update_event,

            static: importUrls.static,
            api_root: importUrls.api_root,
        },
        availableTimelines: [],
        minimized: true,
        id: 1,
        title: "",
        description: "",
        createdBy: -1, // (user accts are for auth/logging purposes)
        isAuthor: false,
        author: '', // user-added string
        categories: [],
        events: [],
        cases: [],
        stats: [],
        firstYear: 1900,
        lastYear: 2000,
        templateEvent: {
            name: "",
            short_description: "",
            long_description: "",
            start_date: "",
            end_date: "",
            url: "",
            color: "",
        },
        templateCase: {
            url: "",
            name: "",
            citation: "",
            short_description: "",
            long_description: "",
            jurisdiction: "",
            reporter: "",
            decision_date: "",
            categories: [],
            color: "",
        },
        templateCategory: {
            name: "",
            shape: "",
            color: ""
        },
        missingCases: {}
    },
    mutations: {
        expandMobileEvents(state) {
            state.mobileEventsExpanded = true
        },
        setBreakPoint(state, newBreakPoint) {
            state.breakPoint = newBreakPoint
        },
        unExpandMobileEvents(state) {
            state.mobileEventsExpanded = false
        },
        toggleMinimized(state) {
            state.minimized = !state.minimized
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {
            state.title = json.title;
            state.author = json.author ? json.author : "CAP User";
            state.description = json.description;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases;
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id;
        },
        setCreatedBy(state, createdBy) {
            state.createdBy = createdBy;
        },
        setAuthor(state, isAuthor) {
            state.isAuthor = isAuthor;
        },
        setCategories(state, categories) {
            state.categories = categories;
        },
        setStats(state, stats) {
            state.stats = stats;
        },
        setFirstYear(state, year) {
            state.firstYear = year;
        },
        setLastYear(state, year) {
            state.lastYear = year;
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
        addCase(state, case_object) {
            case_object.id = this.generateUUID();
            this.dispatch('requestAddUpdateSubobject', 'cases', case_object);
        },
        updateCase(state, case_object) {
            this.dispatch('requestAddUpdateSubobject', 'cases', case_object);
        },
        deleteCase(state, id) {
            this.dispatch('requestDeleteSubobject', 'cases', id);
        },
        updateEvent(state, event_object) {
            this.dispatch('requestAddUpdateSubobject', 'events', event_object);
        },
        addEvent(state, event_object) {
            event_object.id = this.generateUUID();
            this.dispatch('requestAddUpdateSubobject', 'events', event_object);
        },
        deleteEvent(state, id) {
            this.dispatch('requestDeleteSubobject', 'events', id);
        },
        addUpdateCategory(state, category_object) {
            this.dispatch('requestAddUpdateSubobject', 'categories', category_object);
        },
        deleteCategory(state, id) {
            this.dispatch('requestDeleteSubobject', 'categories', id);
        },

        setMissingCases(state, missingCases) {
            state.missingCases = missingCases;
        }
    },
    getters: {
        breakPoint: state => state.breakPoint,
        isMobile: (state) => {
            return state.breakPoint === 'xs' || state.breakPoint === 'sm';
        },
        mobileEventsExpanded: state => state.mobileEventsExpanded,
        minimized: state => state.minimized,
        cases: state => state.cases,
        choices: state => state.choices,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        notificationMessage: state => state.notificationMessage,
        templateEvent: state => state.templateEvent,
        templateCase: state => state.templateCase,
        templateCategory: state => state.templateCategory,
        empty: (state) => {
            if (state.requestStatus === 'pending') {
                return 'pending'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events') &&
                !Object.prototype.hasOwnProperty.call(state, 'events') ) {
                return 'empty'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events')) {
                return state.cases.length === 0 ? 'empty' : 'populated'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'cases') ) {
                return state.events.length === 0 ? 'empty' : 'populated'
            }
            return state.events.length + state.cases.length === 0 ? 'empty' : 'populated';
        },
        firstYear: (state) => {
            return state.firstYear;
            // if (state.cases.length === 0 && state.events.length === 0) {
            //     return 0
            // }
            // let first_case_year = 9999999;
            // let first_event_year = 9999999;
            // if (state.events.length) {
            //     first_event_year = state.events.reduce((min, e) =>
            //         new Date(e.start_date).getUTCFullYear() < min ? new Date(e.start_date).getUTCFullYear() : min, new Date(state.events[0].start_date).getUTCFullYear());
            // }
            // if (state.cases.length) {
            //     first_case_year = state.cases.reduce((min, c) => new Date(c.decision_date).getUTCFullYear() < min ? new Date(c.decision_date).getUTCFullYear() : min, new Date(state.cases[0].decision_date).getUTCFullYear());
            // }
            // return first_case_year < first_event_year ? first_case_year : first_event_year;
        },
        lastYear: (state) => {
            return state.lastYear;
            // if (state.cases.length === 0 && state.events.length === 0) {
            //     return 0
            // }
            // let last_event_year = 0;
            // let last_case_year = 0;
            // if (state.events.length) {
            //     last_event_year = state.events.reduce((max, e) =>
            //         new Date(e.end_date).getUTCFullYear() > max ? new Date(e.end_date).getUTCFullYear() : max, new Date(state.events[0].end_date).getUTCFullYear());
            // }
            // if (state.cases.length) {
            //     last_case_year = state.cases.reduce((max, e) =>
            //         new Date(e.decision_date).getUTCFullYear() > max ? new Date(e.decision_date).getUTCFullYear() : max, new Date(state.cases[0].decision_date).getUTCFullYear());
            // }
            // return last_case_year > last_event_year ? last_case_year : last_event_year;
        },
        events: (state) => {
            return state.events.sort((a, b) => (a.start_date > b.start_date) ? 1 : -1)
        },
        eventByStartYear: (state) => (year) => {
            return state.events.filter(evt => {
                return new Date(evt.start_date).getUTCFullYear() === year;
            })
        },
        casesByYear: (state) => (year) => {
            return state.cases.filter(cas => {
                return year === new Date(cas.decision_date).getUTCFullYear();
            })
        },
        timeline: (state) => {
            return {
                title: state.title,
                author: state.author,
                events: state.events,
                cases: state.cases,
                categories: state.categories,
                description: state.description
            }
        },
        categories: (state) => {
            return state.categories
        },
        category: (state) => (id) => {
            return state.categories.find(cat => cat.id === id)
        },
        randomColor: (state) => {
            return state.colors[Math.floor(Math.random() * state.colors.length)]
        },
        stats: (state) => {
            return state.stats;
        },
        missingCases: (state) => {
            return state.missingCases;
        }
    },
    actions: {
        saveCategories: function ({commit}, incoming_categories) {
            let new_or_updated_categories = incoming_categories.map((incoming_item) => {

                if (!Object.prototype.hasOwnProperty.call(incoming_item, 'id')) {
                    return {...incoming_item, 'id': store.generateUUID()}
                }

                let update = this.getters.categories.filter((state_item) => {
                    return incoming_item.id === state_item.id && (incoming_item.name !== state_item.name || incoming_item.color !== state_item.color || incoming_item.shape !== state_item.shape);
                }).length > 0;

                return update ? incoming_item : null

            }).filter((cat) => {
                return cat
            });

            let deleted_categories = this.getters.categories.filter((state_item) => {
                return incoming_categories.filter((incoming_item) => {
                    return incoming_item.id === state_item.id
                }) < 1
            });
            deleted_categories.forEach( function (dc) {
               commit('deleteCategory', dc.id);
            } );
            new_or_updated_categories.forEach( function (uc) {
                commit('addUpdateCategory', uc);
            } );
        },
        requestCreateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .post(this.state.urls.chronolawgic_api_create)
                .then(response => response.data)
                .then(new_tl => {
                    if (new_tl.status === "ok") {
                        this.dispatch('requestTimelineList');
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', 'Timeline Created')
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
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
                commit('setNotificationMessage', "error deleting timeline: " + getBestError(error))
            })
        },
        requestUpdateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            let json = JSON.stringify({timeline: this.getters.timeline});
            axios
                .post(this.state.urls.chronolawgic_api_update + this.state.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Timeline Saved")
                    }
                ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
         requestDeleteSubobject: function ({commit}, type, id) {
            commit('setRequestStatus', 'pending');
            let url = this.state.urls.api_delete_subobject
                .replace('__TIMELINE_ID__', this.state.id)
                .replace('__SUBOBJECT_ID__', id)
                .replace('__SUBOBJECT_TYPE__', type);

            return axios
                .delete(url, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(status => {
                        this.dispatch('requestRefreshTimeline').then(() => {
                            commit('setRequestStatusTerminal', status.status);
                            commit('setNotificationMessage', status.message)
                        })
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestAddUpdateSubobject: function ({commit}, type, subobject) {
            commit('setRequestStatus', 'pending');
            let url = this.state.urls.api_delete_subobject
                .replace('__TIMELINE_ID__', this.state.id)
                .replace('__SUBOBJECT_ID__', subobject.id)
                .replace('__SUBOBJECT_TYPE__', type);

            let case_update_payload = JSON.stringify(subobject);
            return axios
                .post(url, case_update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(status => {
                        this.dispatch('requestRefreshTimeline').then(() => {
                            commit('setRequestStatusTerminal', status.status);
                            commit('setNotificationMessage', status.message)
                        })
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestTimeline: function ({commit}, timelineId) {
            // clear timeline if it exists
            commit('setTimelineId', '');
            commit('setTimeline', {title: ''});

            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimelineId', timeline['id']);
                        commit('setTimeline', timeline['timeline']);
                        commit('setCreatedBy', timeline['created_by']);
                        commit('setAuthor', timeline['is_owner'])
                        commit('setStats', timeline['stats'])
                        commit('setFirstYear', timeline['first_year'])
                        commit('setLastYear', timeline['last_year'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error retrieving timeline: " + getBestError(error))
            })
        },
        requestRefreshTimeline: function ({commit, getters}) {
            // clear timeline if it exists
            return axios
                .get(this.state.urls.chronolawgic_api_retrieve + getters.id)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimeline', timeline['timeline']);
                    }
                }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error retrieving timeline: " + getBestError(error))
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
                commit('setNotificationMessage', "error retrieving timeline list: " + getBestError(error))
            })
        },
        requestUpdateAdmin: function ({commit}, data) {
            commit('setRequestStatus', 'pending');
            let author = data.author.trim();
            let json = JSON.stringify({
                title: data.title,
                // don't allow empty strings
                author: author ? author : "CAP User",
                description: data.description,
            });

            return axios
                .post(this.state.urls.chronolawgic_api_update_admin + data.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Change Saved")
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
                })
        },
        requestCreateH2OTimeline: function ({commit}, data) {
            let json = JSON.stringify(data)
            return axios.post(this.state.urls.chronolawgic_api_create_h2o, json, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => response.data)
                .then(
                    (new_tl) => {
                        if (new_tl.status === "ok") {
                            this.dispatch('requestTimelineList');
                        }
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Timeline Created")
                        return new_tl
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
                    return error
                })

        }
    }
});

store.generateUUID = () => {
    // https://stackoverflow.com/a/2117523/2247227
    return 'xxxxxxxxxx'.replace(/[xy]/g, function (c) {
        let r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}


export default store;